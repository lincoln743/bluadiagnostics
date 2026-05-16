"""
Agente Fora-de-Escopo — recusa educada determinística (zero LLM).

Quando o supervisor detecta off-topic (clima, finanças, política, etc.),
respondemos com template fixo que:
- Reconhece a pergunta sem desrespeitar
- Reorienta para o que o Blua sabe ajudar
- Lista bullets das capacidades

Por que sem LLM aqui?
- Determinismo (mesma resposta para mesma intent, fácil de testar)
- Zero token gasto
- Sem risco do LLM tentar responder a pergunta off-topic mesmo após instrução
"""
from __future__ import annotations

from typing import Any

from src.graph.state import BluaState
from src.prompts.system_prompts import FORA_ESCOPO_RESPOSTA_TEMPLATE


def fora_escopo_node(state: BluaState) -> dict[str, Any]:
    """Nó do grafo — responde com template de recusa educada e finaliza."""
    paciente = state.get("paciente", {})
    nome = paciente.get("nome_apelido")

    # Personaliza com nome se disponível
    if nome:
        resposta = f"Oi, {nome}! " + FORA_ESCOPO_RESPOSTA_TEMPLATE.lstrip("Oi! ")
    else:
        resposta = FORA_ESCOPO_RESPOSTA_TEMPLATE

    return {
        "mensagens": [{"role": "assistant", "content": resposta}],
        "agentes_acionados": ["fora_escopo"],
        "conversa_finalizada": False,  # paciente pode reformular
    }
