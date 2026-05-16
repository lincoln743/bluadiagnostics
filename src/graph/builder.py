"""
Builder do StateGraph LangGraph.

ARQUITETURA DO GRAFO:

    START
      ↓
    [supervisor]   ← classifica intent (rule-based + LLM fallback + red flag check)
      ↓ (conditional edge: route_from_supervisor)
      ├─→ [triagem]      → END
      ├─→ [prescricao]   → END
      ├─→ [escalada]     → END
      └─→ [fora_escopo]  → END

5 nós, 1 conditional edge (do supervisor para cada agente especialista).
Os agentes terminais não precisam de conditional edge — basta arestar direto
para END após geração de resposta.

CHECKPOINTER:
- MemorySaver (em memória) — suficiente para Sprint 2.
- Permite invocação multi-turno: o estado persiste entre invoke() consecutivos
  desde que o mesmo thread_id seja usado.
- Para produção: trocar por PostgresSaver ou SqliteSaver.
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.agents.escalada import escalada_node
from src.agents.fora_escopo import fora_escopo_node
from src.agents.prescricao import prescricao_node
from src.agents.supervisor import supervisor_node
from src.agents.triagem import triagem_node
from src.graph.state import BluaState


# ============================================================
# Função de roteamento (conditional edge)
# ============================================================

def route_from_supervisor(state: BluaState) -> str:
    """
    Decide para qual agente especialista o supervisor envia o controle.
    Lê state["intent"] (preenchido pelo supervisor_node) e retorna o nome
    do próximo nó a executar.

    Esta função é PURA — não modifica o estado, só lê. LangGraph chama ela
    DEPOIS de supervisor_node completar a atualização do estado.
    """
    intent = state.get("intent")

    if intent == "escalada":
        return "escalada"
    elif intent == "prescricao":
        return "prescricao"
    elif intent == "triagem":
        return "triagem"
    elif intent == "fora_de_escopo":
        return "fora_escopo"
    else:
        # Intent None ou desconhecido — fallback seguro para triagem
        # (melhor uma autoavaliação a mais do que rejeitar erradamente)
        return "triagem"


# ============================================================
# Builder
# ============================================================

def build_graph(use_checkpointer: bool = True):
    """
    Monta o StateGraph completo.

    Args:
        use_checkpointer: se True, usa MemorySaver para suportar conversas
                          multi-turno. Para um único turno isolado (testes),
                          False economiza overhead.

    Returns:
        CompiledStateGraph pronto para `.invoke(state)` ou `.stream(state)`.
    """
    # 1. Cria o grafo tipado com BluaState
    builder = StateGraph(BluaState)

    # 2. Adiciona os 5 nós
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("triagem", triagem_node)
    builder.add_node("prescricao", prescricao_node)
    builder.add_node("escalada", escalada_node)
    builder.add_node("fora_escopo", fora_escopo_node)

    # 3. Edge: START → supervisor (sempre)
    builder.add_edge(START, "supervisor")

    # 4. Conditional edge: supervisor → {triagem | prescricao | escalada | fora_escopo}
    builder.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "triagem": "triagem",
            "prescricao": "prescricao",
            "escalada": "escalada",
            "fora_escopo": "fora_escopo",
        },
    )

    # 5. Edges terminais: cada agente especialista → END
    builder.add_edge("triagem", END)
    builder.add_edge("prescricao", END)
    builder.add_edge("escalada", END)
    builder.add_edge("fora_escopo", END)

    # 6. Compila com ou sem checkpointer
    if use_checkpointer:
        checkpointer = MemorySaver()
        graph = builder.compile(checkpointer=checkpointer)
    else:
        graph = builder.compile()

    return graph


# ============================================================
# Helper para uso comum (Streamlit e smoke test)
# ============================================================

def invoke_with_message(
    graph,
    user_message: str,
    paciente_id: str = "BNF-04821",
    nome_apelido: str = "Maria",
    thread_id: str = "default",
    historico_anterior: list[dict] | None = None,
) -> dict:
    """
    Helper para invocar o grafo com uma mensagem nova.

    Args:
        graph: grafo compilado (vindo de build_graph())
        user_message: texto do usuário neste turno
        paciente_id: ID pseudonimizado (BNF-XXXXX)
        nome_apelido: primeiro nome para personalização
        thread_id: identificador da conversa (para checkpointer)
        historico_anterior: mensagens de turnos anteriores (opcional)

    Returns:
        Estado final após este turno.
    """
    from src.graph.state import estado_inicial

    state = estado_inicial({
        "paciente_id": paciente_id,
        "nome_apelido": nome_apelido,
    })

    if historico_anterior:
        state["mensagens"] = list(historico_anterior) + [
            {"role": "user", "content": user_message}
        ]
    else:
        state["mensagens"] = [{"role": "user", "content": user_message}]

    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke(state, config=config)
