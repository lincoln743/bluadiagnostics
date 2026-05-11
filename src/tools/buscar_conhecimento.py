"""
Tool: buscar_conhecimento_clinico

Expõe o retriever RAG como tool — o agente decide quando precisa buscar
contexto em vez de fazer retrieval cego em todo turno.

Vantagem dessa abordagem:
- Reduz custo (não retrieva quando não precisa)
- Permite query reformulation pelo próprio LLM
- Traceability: cada chamada fica registrada em state["tools_chamadas"]

Implementação prevista (Dia 2):
- Função buscar_conhecimento_clinico(query, top_k=4, kb_filter=None) -> dict
- Wrapper sobre ClinicalRetriever
- Retorno: {chunks: [{text, source, score}], total_encontrados}
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 2
