"""
Retriever — interface de consulta à Knowledge Base no ChromaDB.

Usado de dois jeitos:
1. Diretamente por outros módulos: `ClinicalRetriever().retrieve(query)`
2. Como tool exposta para function calling: src/tools/buscar_conhecimento.py

Por que expor como tool em vez de retrieval cego em todo turno?
- Reduz custo: só busca quando o agente decide que precisa
- Permite query reformulation pelo próprio LLM ("falta de ar súbita" pode virar
  "dispneia aguda" antes da busca)
- Traceability: cada chamada fica registrada na trajetória de tools

Custo de inicialização: ~2-3s na primeira instância (carrega modelo de embeddings).
A classe é projetada para ser singleton — instanciar uma vez no startup do app.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.embeddings import SentenceTransformerEmbeddings

from src.config import settings


@dataclass
class RetrievedChunk:
    """Um chunk recuperado, com texto + metadados + score."""
    text: str
    source_file: str
    kb_id: str
    section: str  # breadcrumb h1 > h2 > h3
    score: float  # 0..1 — quanto maior, mais relevante (1 - distance cosine)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialização para JSON (logs, tool result, painel Streamlit)."""
        return {
            "text": self.text,
            "source_file": self.source_file,
            "kb_id": self.kb_id,
            "section": self.section,
            "score": round(self.score, 4),
        }

    @property
    def text_snippet(self) -> str:
        """Snippet curto para UI (primeiros 180 chars)."""
        return self.text[:180] + ("..." if len(self.text) > 180 else "")


class ClinicalRetriever:
    """
    Retriever da Knowledge Base clínica.

    Uso típico:
        retriever = ClinicalRetriever()  # carrega 1x
        chunks = retriever.retrieve("dor torácica irradiando", top_k=4)
        for c in chunks:
            print(c.score, c.source_file, c.text_snippet)

    Filtros por KB:
        # só consulta kb05_red_flags (útil em triagem rápida)
        chunks = retriever.retrieve("AVC", kb_filter="kb05")
    """

    def __init__(
        self,
        persist_dir=None,
        collection_name=None,
        embedding_model=None,
    ):
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        self.collection_name = collection_name or settings.chroma_collection_name
        self.embedding_model_name = embedding_model or settings.embedding_model

        # Lazy: só carrega quando o primeiro retrieve() for chamado
        self._embedder = None
        self._collection = None

    def _ensure_loaded(self) -> None:
        """Lazy-load do modelo + collection."""
        if self._embedder is None:
            self._embedder = SentenceTransformerEmbeddings(
                model_name=self.embedding_model_name
            )
        if self._collection is None:
            if not self.persist_dir.exists():
                raise FileNotFoundError(
                    f"ChromaDB não encontrado em {self.persist_dir}. "
                    "Rode `blua-ingest` primeiro."
                )
            client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            try:
                self._collection = client.get_collection(self.collection_name)
            except Exception as exc:
                raise RuntimeError(
                    f"Collection '{self.collection_name}' não encontrada. "
                    "Rode `blua-ingest` primeiro."
                ) from exc

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        kb_filter: str | None = None,
        min_score: float = 0.0,
    ) -> list[RetrievedChunk]:
        """
        Busca os chunks mais relevantes para a query.

        Args:
            query: pergunta ou texto de busca
            top_k: número máximo de chunks a retornar (default 4)
            kb_filter: se passado, filtra por kb_id (ex: "kb05" só red flags)
            min_score: filtro de qualidade — chunks com score abaixo são descartados

        Returns:
            Lista ordenada por relevância (maior score primeiro), até top_k chunks.
        """
        self._ensure_loaded()

        # Gera embedding da query
        query_embedding = self._embedder.embed_query(query)

        # Monta o filtro ChromaDB se aplicável
        where_clause = {"kb_id": kb_filter} if kb_filter else None

        # Consulta
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause,
        )

        # ChromaDB retorna listas-de-listas (uma por query); pegamos a primeira
        documents = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []

        chunks: list[RetrievedChunk] = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            # ChromaDB cosine distance: 0 = idêntico, 2 = oposto.
            # Convertemos para score 0..1 onde 1 = idêntico.
            score = max(0.0, 1.0 - (dist / 2.0))
            if score < min_score:
                continue

            section_parts = [
                meta.get("h1", ""),
                meta.get("h2", ""),
                meta.get("h3", ""),
            ]
            section = " > ".join([s for s in section_parts if s])

            chunks.append(RetrievedChunk(
                text=doc,
                source_file=meta.get("source_file", "unknown"),
                kb_id=meta.get("kb_id", "unknown"),
                section=section or "(sem seção)",
                score=score,
                metadata=meta,
            ))
        return chunks


@lru_cache(maxsize=1)
def get_retriever() -> ClinicalRetriever:
    """Retorna instância singleton do retriever (lazy-loaded)."""
    return ClinicalRetriever()


def format_chunks_for_prompt(chunks: list[RetrievedChunk]) -> str:
    """
    Formata chunks recuperados como bloco de contexto para injetar no prompt.

    Formato (markdown):
        ### Contexto recuperado da base de conhecimento Care Plus

        **[kb05_red_flags.md → Cardiovascular]** (relevância: 0.87)
        > Dor torácica irradiando para braço esquerdo, mandíbula ou costas...

        **[kb02_bulas_resumidas.md → Losartana]** (relevância: 0.72)
        > Losartana 50mg, antagonista do receptor AT1...
    """
    if not chunks:
        return "_Nenhum contexto recuperado da base de conhecimento._"

    blocks = ["### Contexto recuperado da base de conhecimento Care Plus\n"]
    for c in chunks:
        blocks.append(
            f"**[{c.source_file} → {c.section}]** (relevância: {c.score:.2f})\n"
            f"> {c.text}\n"
        )
    return "\n".join(blocks)
