"""
Smoke test do RAG.

Roda queries representativas e verifica se o retrieval traz docs sensatos.
NÃO é um teste unitário formal — é um sanity check humano-legível.

Uso:
    python scripts/rag_smoke.py
    python scripts/rag_smoke.py "minha query custom"

Espera-se ANTES de rodar:
    1. blua-ingest executado com sucesso
    2. data/chroma_db/ populado
"""
from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.tools.buscar_conhecimento import buscar_conhecimento_clinico

console = Console()


# Casos de sanity-check: query + qual KB esperamos que apareça no top-1
SMOKE_QUERIES = [
    ("dor torácica irradiando para braço esquerdo, suor frio", "kb05"),
    ("posso tomar ibuprofeno com losartana", "kb02"),
    ("posso fazer teleconsulta em qualquer especialidade", "kb03"),
    ("quando devo procurar pronto-socorro em vez de teleconsulta", "kb04"),
    ("classificação de urgência no protocolo Manchester", "kb01"),
    ("AVC sinais de alerta", "kb05"),
    ("interação medicamentosa varfarina", "kb02"),
]


def run_single(query: str, expected_kb: str | None = None) -> bool:
    """Roda uma query e mostra resultado. Retorna True se top-1 bate com expected."""
    result = buscar_conhecimento_clinico(query=query, top_k=3)

    console.print()
    console.print(Panel(
        f"[bold cyan]Query:[/bold cyan] {query}\n"
        f"[dim]Esperado top-1 em: {expected_kb or 'qualquer'}[/dim]",
        title=f"🔍 {result['total_encontrados']} chunks encontrados",
        border_style="cyan",
    ))

    if not result["chunks"]:
        console.print("[red]❌ Nenhum chunk recuperado![/red]")
        return False

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Rank", justify="center", style="dim", width=4)
    table.add_column("KB", style="cyan", width=6)
    table.add_column("Score", justify="right", style="green", width=7)
    table.add_column("Seção", style="yellow", width=30)
    table.add_column("Texto (snippet)", style="white")

    for idx, chunk in enumerate(result["chunks"], 1):
        snippet = chunk["text"][:120].replace("\n", " ") + "..."
        table.add_row(
            str(idx),
            chunk["kb_id"],
            f"{chunk['score']:.3f}",
            chunk["section"][:30],
            snippet,
        )
    console.print(table)

    if expected_kb:
        top1_kb = result["chunks"][0]["kb_id"]
        match = top1_kb == expected_kb
        marker = "[green]✅ MATCH[/green]" if match else "[red]❌ MISS[/red]"
        console.print(
            f"   Top-1: {top1_kb} | Esperado: {expected_kb} | {marker}"
        )
        return match
    return True


def main() -> None:
    # Custom query passada via CLI
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        run_single(query)
        return

    # Suite padrão
    console.print("[bold]🩺 BluaDiagnostics — RAG Smoke Test[/bold]")
    console.print(f"[dim]Rodando {len(SMOKE_QUERIES)} queries de sanity check[/dim]")

    hits = 0
    for query, expected in SMOKE_QUERIES:
        if run_single(query, expected):
            hits += 1

    console.print()
    pct = (hits / len(SMOKE_QUERIES)) * 100
    color = "green" if pct >= 70 else "yellow" if pct >= 50 else "red"
    console.print(
        f"[bold {color}]Resultado: {hits}/{len(SMOKE_QUERIES)} acertos "
        f"({pct:.0f}%)[/bold {color}]"
    )
    console.print("[dim]Acertar 5/7 ou mais é bom sinal. Misses isolados são esperados[/dim]")
    console.print("[dim](principalmente kb04 vs kb01, que têm overlap conceitual).[/dim]")


if __name__ == "__main__":
    main()
