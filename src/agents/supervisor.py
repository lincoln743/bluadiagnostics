"""
Agente Supervisor — v1.2 (Dia 5).

PIPELINE V1.2 (atualizado):
    1. moderar()              [NOVO] → bloqueia jailbreaks ANTES de tudo
    2. detectar_hibrido()             → red flag (rule + LLM fallback)
    3. validar_hibrido()              → escopo (rule + LLM fallback)
    4. _classificar_rule_based()      → keywords óbvias
    5. _classificar_via_llm()         → LLM com few-shot

Mudanças v1.1 → v1.2:
- Adicionado step 1: moderação anti-jailbreak (curto-circuita para fora_escopo)
- Trocado detectar() rule-only por detectar_hibrido() (LLM fallback)
- Trocado validar_escopo() puro por validar_hibrido() (LLM fallback)
- Campo motivo_classificacao agora distingue "jailbreak" de "off-topic legítimo"
"""
from __future__ import annotations

import json
import re
from typing import Any

from src.graph.state import BluaState, Intent, RedFlagInfo
from src.guardrails.moderation import moderar
from src.guardrails.red_flags import detectar_hibrido as detectar_red_flag
from src.guardrails.scope import validar_hibrido as validar_escopo
from src.prompts.system_prompts import SUPERVISOR_FEW_SHOTS, montar_supervisor_messages
from src.providers.llm_provider import get_provider


# ============================================================
# Rule-based intent (v1.0 — preservado)
# ============================================================

RULE_PATTERNS: dict[Intent, list[str]] = {
    "prescricao": [
        r"\b(receita|prescriç[ãa]o|prescrever|prescreve)\b",
        r"\b(passa|me passe|pode passar) (uma )?(receita|prescriç[ãa]o)\b",
        r"\brenovar (a )?receita\b",
        r"\bantibi[oó]tico\b",
        r"\bme prescreva\b",
    ],
    "triagem": [
        r"\b(estou com|sinto|sentindo|tenho|tive)\b.*\b(dor|febre|tosse|n[aá]usea|tontura|cansaço|fadiga)\b",
        r"\b(dor|febre|tosse) (de|h[aá]) \d+ dias?\b",
        r"\bposso tomar\b",
        r"\bpode tomar\b.*\bcom\b",
        r"\b(efeito colateral|reaç[ãa]o adversa)\b",
    ],
    "escalada": [
        r"\bquero (falar|conversar) (com|um) (m[eé]dico|humano|atendente|pessoa)\b",
        r"\bcom (um |o |a )?m[eé]dico (agora|urgente)\b",
        r"\bn[aã]o quero falar com (bot|rob[oô]|ia)\b",
    ],
}


def _classificar_rule_based(mensagem: str) -> tuple[Intent | None, str]:
    for intent, patterns in RULE_PATTERNS.items():
        for p in patterns:
            m = re.search(p, mensagem, re.IGNORECASE | re.UNICODE)
            if m:
                return intent, f"rule-based: padrão '{m.group(0)}' → {intent}"
    return None, ""


# ============================================================
# LLM classifier (v1.0 — preservado)
# ============================================================

VALID_INTENTS = {"triagem", "prescricao", "escalada", "fora_de_escopo"}


def _classificar_via_llm(
    nova_mensagem: str,
    historico: list[dict[str, Any]],
) -> tuple[Intent, str]:
    """Chama Groq com few-shot. Parsing defensivo."""
    provider = get_provider()
    messages = montar_supervisor_messages(historico, nova_mensagem)

    response = provider.chat_completion(
        messages=messages,
        temperature=0.1,
        max_tokens=120,
    )

    text = response.text.strip()
    text_clean = re.sub(r"^```(?:json)?\s*", "", text)
    text_clean = re.sub(r"\s*```$", "", text_clean)

    try:
        data = json.loads(text_clean)
        intent_raw = str(data.get("intent", "")).strip().lower()
        motivo = str(data.get("motivo", "sem motivo informado"))

        if intent_raw in VALID_INTENTS:
            return intent_raw, f"llm: {motivo}"
        else:
            return "triagem", f"llm: intent inválido '{intent_raw}' — fallback triagem"
    except json.JSONDecodeError:
        return "triagem", f"llm: JSON inválido — fallback triagem (raw: {text[:60]}...)"


# ============================================================
# Nó do grafo — V1.2 com moderação
# ============================================================

def supervisor_node(state: BluaState) -> dict[str, Any]:
    """Nó do LangGraph. Pipeline: moderação → red flag → escopo → intent."""
    user_msgs = [m for m in state["mensagens"] if m.get("role") == "user"]
    if not user_msgs:
        return {
            "intent": "fora_de_escopo",
            "agentes_acionados": ["supervisor"],
            "motivo_classificacao": "sem mensagem do usuário no histórico",
            "turno_atual": state.get("turno_atual", 0) + 1,
        }

    ultima_msg = user_msgs[-1].get("content", "")

    # ========== 1. MODERAÇÃO (NOVO V1.2 — prioridade máxima) ==========
    mod = moderar(ultima_msg)
    if mod.bloqueado:
        return {
            "intent": "fora_de_escopo",  # reusa agente fora_escopo
            "agentes_acionados": ["supervisor"],
            "motivo_classificacao": (
                f"jailbreak/moderation bloqueado: {mod.categoria} "
                f"(severidade {mod.severidade}, gatilho: '{mod.trecho_gatilho}')"
            ),
            "turno_atual": state.get("turno_atual", 0) + 1,
        }

    # ========== 2. RED FLAG (V1.2: agora híbrido) ==========
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
            "motivo_classificacao": (
                f"red flag detectada via {rf.fonte_deteccao}: {rf.categoria} "
                f"(gatilho: '{rf.frase_gatilho}')"
            ),
            "turno_atual": state.get("turno_atual", 0) + 1,
        }

    # ========== 3. ESCOPO (V1.2: agora híbrido) ==========
    scope = validar_escopo(ultima_msg)
    if not scope.no_escopo:
        return {
            "intent": "fora_de_escopo",
            "agentes_acionados": ["supervisor"],
            "motivo_classificacao": f"fora de escopo via {scope.fonte_deteccao}: {scope.motivo}",
            "turno_atual": state.get("turno_atual", 0) + 1,
        }

    # ========== 4. CLASSIFICAÇÃO RULE-BASED ==========
    intent_rb, motivo_rb = _classificar_rule_based(ultima_msg)
    if intent_rb is not None:
        return {
            "intent": intent_rb,
            "agentes_acionados": ["supervisor"],
            "motivo_classificacao": motivo_rb,
            "turno_atual": state.get("turno_atual", 0) + 1,
        }

    # ========== 5. CLASSIFICAÇÃO LLM (fallback) ==========
    intent_llm, motivo_llm = _classificar_via_llm(ultima_msg, state["mensagens"])
    return {
        "intent": intent_llm,
        "agentes_acionados": ["supervisor"],
        "motivo_classificacao": motivo_llm,
        "turno_atual": state.get("turno_atual", 0) + 1,
    }


# ============================================================
# Versão standalone para smoke test
# ============================================================

def classificar(mensagem: str, historico: list[dict] | None = None) -> dict[str, Any]:
    """Versão para testar isolado do grafo."""
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
