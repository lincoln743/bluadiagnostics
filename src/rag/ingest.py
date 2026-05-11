"""
Pipeline de ingestão da Knowledge Base no ChromaDB.

Lê os 5 documentos da Sprint 1 (kb01_protocolo_manchester, kb02_bulas_resumidas,
kb03_politica_telemedicina, kb04_cartilha_beneficiario, kb05_red_flags) de
data/knowledge_base/, faz chunking, gera embeddings e persiste em ChromaDB.

Uso:
    python -m src.rag.ingest
    # ou via script registrado: blua-ingest

Implementação prevista (Dia 1-2):
- Chunking: RecursiveCharacterTextSplitter, chunk_size=600, overlap=80
  (valores escolhidos para caber em ~1 parágrafo médico médio sem cortar contexto)
- Embeddings: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
  (multilíngue PT-BR, 118MB, roda local sem custo)
- Metadados por chunk: {source_file, kb_id (kb01..kb05), chunk_index, section}
- Idempotência: drop_collection() opcional via flag --reset
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 1-2
# Implementar:
# 1. load_kb_files() -> List[Dict[source, text, kb_id]]
# 2. chunk_documents(docs) -> List[Document] usando RecursiveCharacterTextSplitter
# 3. embed_and_store(chunks) -> persiste em ChromaDB
# 4. main() CLI com flags --reset, --kb-dir
# 5. Sanity check no final: query "dor no peito" deve retornar chunks de kb05_red_flags


def main() -> None:
    """Entrypoint CLI registrado em pyproject.toml como blua-ingest."""
    raise NotImplementedError("Implementar Dia 1-2 da Sprint 2")


if __name__ == "__main__":
    main()
