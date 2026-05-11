"""
Agente Supervisor — roteador central do sistema multi-agente.

Pipeline de decisão (em ordem):
    1. Detector de red flag (rule-based)  → intent="escalada" se positivo
    2. Validador de escopo (rule-based)   → intent="fora_de_escopo" se off-topic
    3. Classificação híbrida de intent:
       3a. Rule-based (keywords)          → retorna se confiante
       3b. LLM fallback (Groq Llama 3.1)  → cobre casos ambíguos

Esse design ATENDE ao princípio "defesa em profundidade":
- Red flags: NUNCA dependem do LLM. Garantia determinística.
- Off-topic óbvio: rule-based rejeita rápido sem gastar token.
- Casos sutis: LLM com few-shot decide.

Updates ao state retornados como dict (LangGraph faz merge automático):
    {
        "intent": "...",
        "agentes_acionados": ["supervisor"],
        "red_flags_detectadas": [...] (opcional),
        "motivo_classificacao": "rule|llm|fallback - explicação",
        "turno_atual": state["turno_atual"] + 1,
    }
"""
from __future__ import annotations

import json
import re
from typing import Any

from src.graph.state import BluaState, Intent, RedFlagInfo
from src.guardrails.red_flags import detectar as detectar_red_flag
from src.guardrails.scope import validar_escopo
from src.prompts.system_prompts import SUPERVISOR_FEW_SHOTS, montar_supervisor_messages
from src.providers.llm_provider import get_provider


# ============================================================
# Classificação rule-based — keywords óbvias por intent
# ============================================================

RULE_PATTERNS: dict[Intent, list[str]] = {
    "prescricao": [
        r"\b(receita|prescriç[ãa]o|prescrever|prescreve)\b",
        r"\b(passa|me passe|pode passar) (uma )?(receita|prescriç[ãa]o)\b",
        r"\brenovar (a )?receita\b",
        r"\bantibi[oó]tico\b",  # pedido típico
        r"\bme prescreva\b",
    ],
    "triagem": [
        # Sintomas comuns — alta confiança
        r"\b(estou com|sinto|sentindo|tenho|tive)\b.*\b(dor|febre|tosse|n[aá]usea|tontura|cansaço|fadiga)\b",
        r"\b(dor|febre|tosse) (de|h[aá]) \d+ dias?\b",
        # Dúvida sobre uso de medicação (não pedido de prescrição)
        r"\bposso tomar\b",
        r"\bpode tomar\b.*\bcom\b",  # interação
        r"\b(efeito colateral|reaç[ãa]o adversa)\b",
    ],
    "escalada": [
        # Pedidos explícitos de humano (red flag PRÓPRIA já cobre urgência clínica)
        r"\bquero (falar|conversar) (com|um) (m[eé]dico|humano|atendente|pessoa)\b",
        r"\bcom (um |o |a )?m[eé]dico (agora|urgente)\b",
        r"\bn[aã]o quero falar com (bot|rob[oô]|ia)\b",
    ],
}


def _classificar_rule_based(mensagem: str) -> tuple[Intent | None, str]:
    """
    Tenta classificar por regex. Retorna (intent, motivo) ou (None, "").
    Intent None significa: rule-based não conseguiu decidir; vai para LLM.
    """
    for intent, patterns in RULE_PATTERNS.items():
        for p in patterns:
            m = re.search(p, mensagem, re.IGNORECASE | re.UNICODE)
            if m:
                return intent, f"rule-based: padrão '{m.group(0)}' → {intent}"
    return None, ""


# ============================================================
# Classificação via LLM (fallback)
# ============================================================

VALID_INTENTS = {"triagem", "prescricao", "escalada", "fora_de_escopo"}


def _classificar_via_llm(
    nova_mensagem: str,
    historico: list[dict[str, Any]],
) -> tuple[Intent, str]:
    """
    Chama Groq com few-shot. Faz parsing defensivo do JSON.
    Em caso de erro, fallback para "triagem" (default seguro).
    """
    provider = get_provider()
    messages = montar_supervisor_messages(historico, nova_mensagem)

    response = provider.chat_completion(
        messages=messages,
        temperature=0.1,   # determinístico para classificação
        max_tokens=120,    # JSON curto
    )

    text = response.text.strip()

    # Parsing defensivo — o LLM pode envolver em ```json ```, vamos limpar
    text_clean = re.sub(r"^```(?:json)?\s*", "", text)
    text_clean = re.sub(r"\s*```$", "", text_clean)

    try:
        data = json.loads(text_clean)
        intent_raw = str(data.get("intent", "")).strip().lower()
        motivo = str(data.get("motivo", "sem motivo informado"))

        if intent_raw in VALID_INTENTS:
            return intent_raw, f"llm: {motivo}"
        else:
            return "triagem", f"llm: intent inválido '{intent_raw}' — fallback para triagem"
    except json.JSONDecodeError:
        return "triagem", f"llm: JSON inválido na resposta — fallback para triagem (raw: {text[:60]}...)"


# ============================================================
# Nó do grafo — supervisor_node
# ============================================================

def supervisor_node(state: BluaState) -> dict[str, Any]:
    """
    Nó do LangGraph. Lê a última mensagem do usuário e classifica intent.

    Não escreve resposta para o usuário — só roteia.

    Retorna dict com chaves a atualizar no estado (LangGraph faz merge).
    """
    # Pega última mensagem do usuário no histórico
    user_msgs = [m for m in state["mensagens"] if m.get("role") == "user"]
    if not user_msgs:
        return {
            "intent": "fora_de_escopo",
            "agentes_acionados": ["supervisor"],
            "motivo_classificacao": "sem mensagem do usuário no histórico",
            "turno_atual": state.get("turno_atual", 0) + 1,
        }

    ultima_msg = user_msgs[-1].get("content", "")

    # ========== 1. RED FLAG (prioridade máxima) ==========
    rf = detectar_red_flag(ultima_msg)
    if rf.detectada:
        red_flag_info: RedFlagInfo = {
            "categoria": rf.categoria or "desconhecida",
            "frase_gatilho": rf.frase_gatilho,
            "severidade": rf.severidade,
            "fonte_deteccao": rf.fonte_deteccao,
        }
        return {
            "intent": "escalada",
            "agentes_acionados": ["supervisor"],
            "red_flags_detectadas": [red_flag_info],
            "requer_escalada_humana": True,
            "motivo_classificacao": f"red flag detectada: {rf.categoria} (gatilho: '{rf.frase_gatilho}')",
            "turno_atual": state.get("turno_atual", 0) + 1,
        }

    # ========== 2. ESCOPO ==========
    scope = validar_escopo(ultima_msg)
    if not scope.no_escopo:
        return {
            "intent": "fora_de_escopo",
            "agentes_acionados": ["supervisor"],
            "motivo_classificacao": f"fora de escopo: {scope.motivo}",
            "turno_atual": state.get("turno_atual", 0) + 1,
        }

    # ========== 3a. CLASSIFICAÇÃO RULE-BASED ==========
    intent_rb, motivo_rb = _classificar_rule_based(ultima_msg)
    if intent_rb is not None:
        return {
            "intent": intent_rb,
            "agentes_acionados": ["supervisor"],
            "motivo_classificacao": motivo_rb,
            "turno_atual": state.get("turno_atual", 0) + 1,
        }

    # ========== 3b. CLASSIFICAÇÃO LLM (fallback para ambíguos) ==========
    intent_llm, motivo_llm = _classificar_via_llm(ultima_msg, state["mensagens"])
    return {
        "intent": intent_llm,
        "agentes_acionados": ["supervisor"],
        "motivo_classificacao": motivo_llm,
        "turno_atual": state.get("turno_atual", 0) + 1,
    }


# ============================================================
# Versão "standalone" para uso em smoke test / debugging
# ============================================================

def classificar(mensagem: str, historico: list[dict] | None = None) -> dict[str, Any]:
    """
    Versão simplificada para testar isolado do grafo.

    Uso:
        from src.agents.supervisor import classificar
        r = classificar("Estou com dor no peito")
        print(r["intent"])           # "escalada"
        print(r["motivo"])           # "red flag detectada: cardiovascular..."
    """
    from src.graph.state import estado_inicial

    state = estado_inicial()
    historico = historico or []
    state["mensagens"] = historico + [{"role": "user", "content": mensagem}]

    update = supervisor_node(state)
    return {
        "intent": update["intent"],
        "motivo": update["motivo_classificacao"],
        "red_flags": update.get("red_flags_detectadas", []),
        "raw_update": update,
    }
