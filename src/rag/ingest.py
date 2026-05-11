"""
Pipeline de ingestão da Knowledge Base no ChromaDB.

Estratégia de chunking: HÍBRIDA
1. Primeiro, MarkdownHeaderTextSplitter quebra por headers (#, ##, ###)
   — preserva integridade semântica das seções
2. Depois, RecursiveCharacterTextSplitter (chunk=600, overlap=80) divide
   chunks grandes ainda por dentro, mantendo o breadcrumb dos headers
   como metadado

Vantagem: "Red Flags Neurológicas" não vaza para "Red Flags Cardiovasculares"
no retrieval, mas seções longas ainda são quebradas em pedaços digeríveis.

Uso:
    blua-ingest                  # ingest normal
    blua-ingest --reset          # apaga collection antes
    blua-ingest --kb-dir PATH    # override do diretório da KB
    blua-ingest --dry-run        # só mostra o que faria, sem persistir
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from rich.console import Console
from rich.table import Table

from src.config import settings

console = Console()

# Configuração do chunking
HEADERS_TO_SPLIT_ON = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]
CHUNK_SIZE = 600       # caracteres — equivale a ~1 parágrafo médico médio
CHUNK_OVERLAP = 80     # 13% de overlap — suficiente para não cortar contexto


def load_kb_files(kb_dir: Path) -> list[dict[str, Any]]:
    """
    Lê os 5 arquivos .md da KB.
    Retorna lista de dicts: {source_file, kb_id, text}.
    """
    docs = []
    md_files = sorted(kb_dir.glob("kb*.md"))

    if not md_files:
        raise FileNotFoundError(
            f"Nenhum arquivo kb*.md encontrado em {kb_dir}. "
            "Confira se os symlinks/cópias estão no lugar."
        )

    for md_path in md_files:
        # Resolve symlinks para ler o conteúdo real
        real_path = md_path.resolve()
        text = real_path.read_text(encoding="utf-8")
        # kb_id = "kb01", "kb02" etc — extraído do nome do arquivo
        kb_id = md_path.stem.split("_")[0]
        docs.append({
            "source_file": md_path.name,
            "kb_id": kb_id,
            "text": text,
            "size_chars": len(text),
        })
    return docs


def chunk_documents(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Aplica chunking híbrido: headers primeiro, char-based depois.
    Retorna lista de chunks com metadados ricos.
    """
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT_ON,
        strip_headers=False,  # mantém o header no texto — ajuda contexto do embedding
    )
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    all_chunks: list[dict[str, Any]] = []

    for doc in docs:
        # Passo 1: quebra por headers
        header_chunks = header_splitter.split_text(doc["text"])

        # Passo 2: para cada header chunk, quebra em char chunks se for grande
        for h_idx, h_chunk in enumerate(header_chunks):
            # h_chunk.page_content é o texto, h_chunk.metadata tem h1/h2/h3
            sub_chunks = char_splitter.split_text(h_chunk.page_content)
            for s_idx, sub_text in enumerate(sub_chunks):
                all_chunks.append({
                    "id": f"{doc['kb_id']}_h{h_idx:02d}_c{s_idx:02d}",
                    "text": sub_text,
                    "metadata": {
                        "source_file": doc["source_file"],
                        "kb_id": doc["kb_id"],
                        "h1": h_chunk.metadata.get("h1", ""),
                        "h2": h_chunk.metadata.get("h2", ""),
                        "h3": h_chunk.metadata.get("h3", ""),
                        "header_chunk_index": h_idx,
                        "sub_chunk_index": s_idx,
                    },
                })
    return all_chunks


def embed_and_store(
    chunks: list[dict[str, Any]],
    persist_dir: Path,
    collection_name: str,
    embedding_model: str,
    reset: bool = False,
) -> None:
    """
    Gera embeddings e persiste no ChromaDB.
    """
    console.print(f"[cyan]→ Carregando modelo de embeddings: {embedding_model}[/cyan]")
    console.print("[dim]  (primeira vez baixa ~118MB — pode demorar 1-2 min)[/dim]")

    embedder = SentenceTransformerEmbeddings(model_name=embedding_model)

    # ChromaDB persistente
    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(persist_dir),
        settings=ChromaSettings(anonymized_telemetry=False),
    )

    if reset:
        try:
            client.delete_collection(collection_name)
            console.print(f"[yellow]⚠ Collection '{collection_name}' deletada (reset)[/yellow]")
        except Exception:
            pass  # não existia ainda

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    console.print(f"[cyan]→ Gerando embeddings para {len(chunks)} chunks...[/cyan]")
    texts = [c["text"] for c in chunks]
    embeddings = embedder.embed_documents(texts)

    console.print(f"[cyan]→ Persistindo no ChromaDB em {persist_dir}...[/cyan]")
    collection.add(
        ids=[c["id"] for c in chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[c["metadata"] for c in chunks],
    )

    total = collection.count()
    console.print(f"[green]✅ {total} chunks persistidos na collection '{collection_name}'[/green]")


def print_ingest_summary(docs: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> None:
    """Tabela de resumo da ingestão para o relatório."""
    table = Table(title="Resumo da Ingestão", show_header=True, header_style="bold magenta")
    table.add_column("Arquivo", style="cyan")
    table.add_column("Tamanho (chars)", justify="right")
    table.add_column("Chunks gerados", justify="right", style="green")

    chunks_por_kb: dict[str, int] = {}
    for c in chunks:
        kb_id = c["metadata"]["kb_id"]
        chunks_por_kb[kb_id] = chunks_por_kb.get(kb_id, 0) + 1

    for doc in docs:
        table.add_row(
            doc["source_file"],
            f"{doc['size_chars']:,}",
            str(chunks_por_kb.get(doc["kb_id"], 0)),
        )
    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{sum(d['size_chars'] for d in docs):,}[/bold]",
        f"[bold]{len(chunks)}[/bold]",
    )
    console.print(table)


def main() -> None:
    """Entrypoint CLI: blua-ingest"""
    parser = argparse.ArgumentParser(description="Ingest da KB para ChromaDB")
    parser.add_argument("--reset", action="store_true", help="Apaga collection antes de ingerir")
    parser.add_argument("--kb-dir", type=Path, default=None, help="Override do diretório da KB")
    parser.add_argument("--dry-run", action="store_true", help="Apenas mostra, não persiste")
    args = parser.parse_args()

    kb_dir = args.kb_dir or settings.knowledge_base_dir

    console.print(f"[bold cyan]🩺 BluaDiagnostics — Ingestão da KB[/bold cyan]")
    console.print(f"[dim]KB dir: {kb_dir}[/dim]")
    console.print(f"[dim]ChromaDB: {settings.chroma_persist_dir}[/dim]")
    console.print(f"[dim]Embedding: {settings.embedding_model}[/dim]")
    console.print()

    # 1. Carrega arquivos
    docs = load_kb_files(kb_dir)
    console.print(f"[green]✓ {len(docs)} arquivos carregados[/green]")

    # 2. Chunking
    chunks = chunk_documents(docs)
    console.print(f"[green]✓ {len(chunks)} chunks gerados[/green]")
    console.print()

    # 3. Resumo
    print_ingest_summary(docs, chunks)
    console.print()

    if args.dry_run:
        console.print("[yellow]⚠ Dry-run: não persistindo no ChromaDB[/yellow]")
        # Mostra 2 amostras
        console.print("\n[bold]Amostras (primeiros 2 chunks):[/bold]")
        for c in chunks[:2]:
            console.print(f"\n[cyan]ID:[/cyan] {c['id']}")
            console.print(f"[cyan]Metadata:[/cyan] {c['metadata']}")
            console.print(f"[cyan]Texto (200 chars):[/cyan] {c['text'][:200]}...")
        return

    # 4. Embed + persist
    embed_and_store(
        chunks=chunks,
        persist_dir=settings.chroma_persist_dir,
        collection_name=settings.chroma_collection_name,
        embedding_model=settings.embedding_model,
        reset=args.reset,
    )

    console.print()
    console.print("[bold green]🎉 Ingestão concluída![/bold green]")
    console.print(f"[dim]Próximo passo: rodar smoke test em notebooks/rag_smoke.py[/dim]")


if __name__ == "__main__":
    main()
