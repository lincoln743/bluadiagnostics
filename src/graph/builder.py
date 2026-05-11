"""
Construtor do grafo LangGraph.

Arquitetura: 4 agentes especializados (Supervisor + Triagem + Prescrição + Escalada)
+ nó de tools compartilhado. Atende ao bônus de "3+ agentes especializados".

Fluxo:
    START
      ↓
    [Supervisor]  ← classifica intent
      ↓ (conditional edge)
    ├─→ [Triagem]      → tools → Supervisor (loop até ter resposta)
    ├─→ [Prescrição]   → tools → Supervisor
    └─→ [Escalada]     → END (sempre termina o fluxo)
      ↓
    END (quando intent == "finalizado")

Implementação prevista (Dia 3-4):
- StateGraph(BluaState)
- Nós: supervisor_node, triagem_node, prescricao_node, escalada_node, tools_node
- Conditional edges: route_from_supervisor (lê state["intent"])
- Compile com checkpointer (MemorySaver) para suportar conversas multi-turno
- Export: build_graph() -> CompiledGraph
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 3-4
# Implementar:
# 1. build_graph() -> CompiledStateGraph
# 2. route_from_supervisor(state) -> Literal["triagem", "prescricao", "escalada", END]
# 3. Persistence com MemorySaver (em memória — suficiente para Sprint 2)
# 4. Interrupção HITL antes do nó de prescricao_node finalizar
#    (requisito: nunca prescrever sem aprovação médica)
