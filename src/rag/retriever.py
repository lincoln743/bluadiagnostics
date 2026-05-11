"""
Retriever — interface para os agentes consultarem a Knowledge Base.

Exposto também como TOOL via function calling (`buscar_conhecimento_clinico`),
permitindo que os agentes decidam quando recuperar contexto em vez de fazer
retrieval cego em todo turno.

Implementação prevista (Dia 2):
- Classe ClinicalRetriever envolvendo ChromaDB collection
- Método retrieve(query, top_k=4, kb_filter=None) -> List[RetrievedChunk]
- RetrievedChunk: {text, source_file, kb_id, score, section}
- Filtro opcional por kb_id (ex: só consultar kb05_red_flags em triagem)
- Logging estruturado de cada retrieval (para observabilidade e evals)
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 2
# Implementar:
# 1. dataclass RetrievedChunk
# 2. classe ClinicalRetriever com __init__(collection_name) e retrieve()
# 3. função format_chunks_for_prompt(chunks) -> str (markdown formatado)
# 4. integração com observability/tracing.py para logar trajetória
