"""
Agente Fora-de-Escopo — v1.1 (Dia 5).

CHANGELOG v1.0 → v1.1:
- Distingue dois sub-casos via state["motivo_classificacao"]:
  * "jailbreak/moderation bloqueado" → mensagem firme anti-jailbreak
  * "fora de escopo" → mensagem acolhedora de redirecionamento normal

Zero LLM — totalmente determinístico.
"""
from __future__ import annotations

from typing import Any

from src.graph.state import BluaState
from src.guardrails.moderation import MENSAGEM_RECUSA_JAILBREAK
from src.prompts.system_prompts import FORA_ESCOPO_RESPOSTA_TEMPLATE


def fora_escopo_node(state: BluaState) -> dict[str, Any]:
    """Recusa educada determinística — distingue jailbreak de off-topic legítimo."""
    paciente = state.get("paciente", {})
    nome = paciente.get("nome_apelido")

    motivo = state.get("motivo_classificacao", "")

    # V1.1: detecta se foi jailbreak (vem da moderação) ou off-topic legítimo
    if "jailbreak" in motivo.lower() or "moderation" in motivo.lower():
        resposta = MENSAGEM_RECUSA_JAILBREAK
        if nome:
            # Substitui "Oi!" inicial por nome
            resposta = resposta.replace("Oi!", f"Oi, {nome}!", 1)
    else:
        if nome:
            resposta = f"Oi, {nome}! " + FORA_ESCOPO_RESPOSTA_TEMPLATE.lstrip("Oi! ")
        else:
            resposta = FORA_ESCOPO_RESPOSTA_TEMPLATE

    return {
        "mensagens": [{"role": "assistant", "content": resposta}],
        "agentes_acionados": ["fora_escopo"],
        "conversa_finalizada": False,
    }
