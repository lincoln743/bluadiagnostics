"""
Estado compartilhado do grafo LangGraph.

Todos os agentes leem e escrevem neste estado. É a única forma de comunicação
entre nós do grafo.

Implementação prevista (Dia 3):
- TypedDict BluaState com todos os campos abaixo
- Reducer functions para campos list (mensagens, red_flags, tools_called)
  usando Annotated[list, operator.add]
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict
from operator import add


# Intent classificado pelo supervisor — define o roteamento
Intent = Literal[
    "triagem",           # check-up digital / autoavaliação
    "prescricao",        # solicitação relacionada a medicação
    "escalada",          # red flag detectada ou usuário pede humano
    "fora_de_escopo",    # pergunta não-clínica
    "finalizado",        # conversa encerrada
]


class PacienteContexto(TypedDict, total=False):
    """Contexto pseudonimizado do beneficiário."""
    paciente_id: str            # BNF-XXXXX
    nome_apelido: str           # primeiro nome ou apelido
    idade: int
    condicoes_cronicas: list[str]
    alergias: list[str]
    medicamentos_em_uso: list[str]


class BluaState(TypedDict):
    """Estado compartilhado do grafo multi-agente."""

    # ---- Conversa ----
    mensagens: Annotated[list[dict[str, Any]], add]  # histórico OpenAI-format

    # ---- Roteamento ----
    intent: Intent | None
    proximo_agente: str | None

    # ---- Contexto clínico ----
    paciente: PacienteContexto
    sintomas_relatados: list[str]
    red_flags_detectadas: Annotated[list[str], add]

    # ---- RAG ----
    docs_recuperados: list[dict[str, Any]]  # último retrieval (para mostrar no Streamlit)

    # ---- Trajetória (para evals e observabilidade) ----
    agentes_acionados: Annotated[list[str], add]
    tools_chamadas: Annotated[list[dict[str, Any]], add]

    # ---- Controle ----
    requer_escalada_humana: bool
    conversa_finalizada: bool
