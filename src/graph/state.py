"""
Estado compartilhado do grafo LangGraph.

Todos os agentes leem e escrevem neste estado. É a única forma de comunicação
entre nós do grafo (não há variáveis globais nem side-effects fora do estado).

Padrão LangGraph:
- Campos `list` recebem `Annotated[list, add]` — o LangGraph concatena valores
  novos com os existentes em vez de sobrescrever.
- Campos escalares são sobrescritos a cada atualização (comportamento default).
"""
from __future__ import annotations

from operator import add
from typing import Annotated, Any, Literal, TypedDict


# Intent classificado pelo supervisor — define o roteamento condicional do grafo.
Intent = Literal[
    "triagem",           # check-up digital / autoavaliação
    "prescricao",        # solicitação relacionada a medicação
    "escalada",          # red flag detectada ou usuário pede humano
    "fora_de_escopo",    # pergunta não-clínica
    "finalizado",        # conversa encerrada
]


class PacienteContexto(TypedDict, total=False):
    """Contexto pseudonimizado do beneficiário (BNF-XXXXX)."""
    paciente_id: str
    nome_apelido: str        # primeiro nome ou apelido
    idade: int
    sexo: str                # "F" | "M" | "outro"
    condicoes_cronicas: list[str]
    alergias: list[str]
    medicamentos_em_uso: list[str]
    ultima_consulta: str     # data ISO ou descrição livre


class RedFlagInfo(TypedDict):
    """Informação de uma red flag detectada (snapshot do guardrail)."""
    categoria: str                    # cardiovascular | neurologica | ...
    frase_gatilho: str                # trecho da mensagem que disparou
    severidade: Literal["alta", "critica"]
    fonte_deteccao: Literal["regra", "llm"]  # como foi detectada


class ToolCallRecord(TypedDict):
    """Registro de uma chamada de tool (para trajetória e observabilidade)."""
    nome: str
    args: dict[str, Any]
    result_resumo: str       # string curta — resultado completo vai em logs JSONL
    timestamp: str           # ISO 8601


class DocRecuperado(TypedDict):
    """Snapshot de um chunk recuperado pelo RAG (para painel Streamlit)."""
    source_file: str
    kb_id: str
    section: str
    score: float
    text_snippet: str


class BluaState(TypedDict):
    """Estado compartilhado do grafo multi-agente."""

    # ---- Conversa ----
    # Histórico em formato OpenAI: [{"role": "user", "content": "..."}, ...]
    mensagens: Annotated[list[dict[str, Any]], add]

    # ---- Roteamento (lido pelas conditional edges) ----
    intent: Intent | None
    proximo_agente: str | None

    # ---- Contexto clínico ----
    paciente: PacienteContexto
    sintomas_relatados: Annotated[list[str], add]
    red_flags_detectadas: Annotated[list[RedFlagInfo], add]

    # ---- RAG (último retrieval — substituído a cada turno) ----
    docs_recuperados: list[DocRecuperado]

    # ---- Trajetória (para evals, observabilidade e painel Streamlit) ----
    agentes_acionados: Annotated[list[str], add]
    tools_chamadas: Annotated[list[ToolCallRecord], add]

    # ---- Controle de fluxo ----
    requer_escalada_humana: bool
    conversa_finalizada: bool

    # ---- Metadados do turno atual ----
    turno_atual: int                    # 1, 2, 3, ...
    motivo_classificacao: str | None    # explicação do supervisor (rule|llm|fallback)


def estado_inicial(paciente: PacienteContexto | None = None) -> BluaState:
    """
    Cria um estado vazio para iniciar uma nova conversa.

    Uso típico:
        state = estado_inicial({"paciente_id": "BNF-04821", "nome_apelido": "Maria"})
        # depois invoca o grafo: graph.invoke(state)
    """
    return BluaState(
        mensagens=[],
        intent=None,
        proximo_agente=None,
        paciente=paciente or PacienteContexto(),
        sintomas_relatados=[],
        red_flags_detectadas=[],
        docs_recuperados=[],
        agentes_acionados=[],
        tools_chamadas=[],
        requer_escalada_humana=False,
        conversa_finalizada=False,
        turno_atual=0,
        motivo_classificacao=None,
    )
