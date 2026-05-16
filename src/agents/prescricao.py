"""
Agente de Prescrição — v1.1 (Dia 4b corrigido)

Mudanças v1.0 → v1.1:
- Detector de vazamento de sintaxe de tool calling
- Retry forçado se vazamento detectado
- Sanitização para fallback seguro (encaminhamento para teleconsulta) se
  retry falhar — em prescrição, fallback SEMPRE encaminha pra humano
- Reusa helpers e detector do triagem.py para DRY
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src.agents.triagem import (
    MAX_TOOL_ITERATIONS,
    _detectar_vazamento,
    _extrair_docs_recuperados,
    _formatar_contexto_paciente,
    _registrar_tool_call,
)
from src.graph.state import BluaState, DocRecuperado, ToolCallRecord
from src.prompts.system_prompts import PRESCRICAO_PROMPT
from src.providers.llm_provider import get_provider
from src.tools import dispatch_tool, get_tool_specs_for_agent


# ============================================================
# Saída estruturada (bloco JSON anexo à resposta)
# ============================================================

def _formatar_instrucao_saida_estruturada() -> str:
    """Bloco que instrui o LLM a terminar com JSON entre <sugestao>...</sugestao>."""
    return """

## FORMATO OBRIGATÓRIO DA SUA RESPOSTA FINAL

Sua resposta deve ter DUAS partes:

PARTE 1 — Texto natural em português:
  Acolhedor, sem jargão. Explica ao paciente o que você está sugerindo e que
  é necessária validação médica.

PARTE 2 — Bloco JSON estruturado entre <sugestao>...</sugestao>:

<sugestao>
{
  "tipo": "sugestao_prescricao" ou "encaminhamento_teleconsulta" ou "nao_prescrever",
  "medicamento": "nome do princípio ativo, se aplicável",
  "dose": "dose com unidade",
  "via": "oral|tópica|inalatória",
  "frequencia": "ex: a cada 8h",
  "duracao": "ex: 5 dias",
  "justificativa": "1-2 frases",
  "alertas": ["alerta 1", "alerta 2"],
  "contraindicacoes_identificadas": ["se houver"],
  "interacoes_identificadas": ["se houver"],
  "encaminhamento": {
    "especialidade": "se aplicável",
    "urgencia": "rotina|prioridade|urgente"
  },
  "requer_revisao_medica": true
}
</sugestao>

REGRAS DO JSON:
- requer_revisao_medica SEMPRE true. Sem exceção.
- Se houver contraindicação por alergia, tipo="nao_prescrever" + encaminhe.
- Para renovação de receita já em uso (ex: Losartana contínua), 
  tipo="encaminhamento_teleconsulta" (renovação exige avaliação médica).
- NUNCA invente doses sem ter consultado o histórico.
"""


# ============================================================
# Sanitizador específico de prescrição
# ============================================================

def _sanitizar_resposta_prescricao(nome_paciente: str | None = None) -> str:
    """
    Fallback seguro para prescrição: encaminha para teleconsulta com bloco
    JSON estruturado já preenchido (encaminhamento de baixo risco).
    """
    saudacao = f"{nome_paciente}, " if nome_paciente else ""
    return f"""\
{saudacao}para garantir uma prescrição segura e adequada ao seu caso, vou te \
encaminhar para uma teleconsulta com um clínico. Ele(a) poderá avaliar seu \
histórico completo e emitir a receita conforme necessário.

Você pode agendar pelo app Blua, seção "Teleconsulta", ou continuar comigo \
aqui se preferir que eu agende para você.

<sugestao>
{{
  "tipo": "encaminhamento_teleconsulta",
  "justificativa": "Encaminhamento padrão para validação médica antes de prescrição.",
  "alertas": ["Toda prescrição requer validação médica."],
  "encaminhamento": {{
    "especialidade": "clinica_medica",
    "urgencia": "prioridade"
  }},
  "requer_revisao_medica": true
}}
</sugestao>

---
⚕️ *Sugestão preliminar — toda prescrição requer validação médica.*
"""


# ============================================================
# Nó do grafo
# ============================================================

def prescricao_node(state: BluaState) -> dict[str, Any]:
    """Nó de prescrição — tool loop com saída estruturada + detector vazamento."""
    provider = get_provider()
    tool_specs = get_tool_specs_for_agent("prescricao")

    system_content = (
        PRESCRICAO_PROMPT
        + _formatar_contexto_paciente(state)
        + _formatar_instrucao_saida_estruturada()
    )

    messages: list[dict[str, Any]] = [{"role": "system", "content": system_content}]
    for msg in state.get("mensagens", []):
        role = msg.get("role")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": msg.get("content", "")})

    tools_executadas: list[ToolCallRecord] = []
    docs_recuperados_turno: list[DocRecuperado] = []
    nome_paciente = state.get("paciente", {}).get("nome_apelido")

    for iteration in range(MAX_TOOL_ITERATIONS):
        response = provider.chat_completion(
            messages=messages,
            tools=tool_specs,
            temperature=0.2,
        )

        # Resposta final (sem tool_calls)
        if not response.tool_calls:
            texto = response.text.strip()

            # FIX V1.1: detectar vazamento
            if _detectar_vazamento(texto):
                # Retry com aviso explícito + sem tools (força texto puro)
                messages.append({"role": "assistant", "content": texto})
                messages.append({
                    "role": "user",
                    "content": (
                        "ATENÇÃO: sua resposta anterior continha sintaxe técnica "
                        "de tool calling (ex: </function>). Reescreva apenas com "
                        "texto natural em português + o bloco <sugestao>...</sugestao> "
                        "obrigatório. Sem menções técnicas."
                    ),
                })
                response_retry = provider.chat_completion(
                    messages=messages,
                    tools=None,
                    temperature=0.2,
                )
                texto = response_retry.text.strip()
                # Falhou de novo? sanitiza com fallback seguro
                if _detectar_vazamento(texto) or len(texto) < 50:
                    texto = _sanitizar_resposta_prescricao(nome_paciente)

            mensagem_final = texto or _sanitizar_resposta_prescricao(nome_paciente)

            return {
                "mensagens": [{"role": "assistant", "content": mensagem_final}],
                "agentes_acionados": ["prescricao"],
                "tools_chamadas": tools_executadas,
                "docs_recuperados": docs_recuperados_turno,
                "requer_escalada_humana": True,  # prescrição sempre exige revisão
            }

        # Tool calls
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": response.text or "",
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                }
                for tc in response.tool_calls
            ],
        }
        messages.append(assistant_msg)

        for tc in response.tool_calls:
            nome = tc["name"]
            args_raw = tc["arguments"]

            try:
                args_dict = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except json.JSONDecodeError:
                args_dict = {}

            resultado = dispatch_tool(nome, args_dict)

            if nome == "buscar_conhecimento_clinico":
                docs_recuperados_turno.extend(_extrair_docs_recuperados(resultado))

            tools_executadas.append(_registrar_tool_call(nome, args_dict, resultado))

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "name": nome,
                "content": json.dumps(resultado, ensure_ascii=False, default=str),
            })

    # Estourou iterações — fallback seguro
    return {
        "mensagens": [{
            "role": "assistant",
            "content": _sanitizar_resposta_prescricao(nome_paciente),
        }],
        "agentes_acionados": ["prescricao"],
        "tools_chamadas": tools_executadas,
        "docs_recuperados": docs_recuperados_turno,
        "requer_escalada_humana": True,
    }


# ============================================================
# Helper público
# ============================================================

def extrair_sugestao_estruturada(resposta_texto: str) -> dict[str, Any] | None:
    """
    Parseia o bloco <sugestao>...</sugestao> da resposta.
    Usado pela UI Streamlit (Dia 8) e pelos evals (Dia 10).
    """
    import re

    match = re.search(
        r"<sugestao>\s*(\{.*?\})\s*</sugestao>",
        resposta_texto,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return None

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
