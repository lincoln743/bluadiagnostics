"""
Smoke test do LangSmith (Dia 9 — BÔNUS Observabilidade SaaS).

Roda 3 cenários determinísticos pelo grafo e instrui o usuário a
verificar no dashboard do LangSmith que os traces apareceram.

NÃO consome muitos tokens — 2 dos 3 cenários são rule-based (zero LLM).

Uso:
    python scripts/test_langsmith.py
"""
from __future__ import annotations

import os
import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.graph.builder import build_graph, invoke_with_message
from src.observability.langsmith_config import (
    get_langsmith_status,
    imprimir_status_startup,
)


console = Console()


# 3 cenários cobrindo diferentes caminhos do grafo
CENARIOS = [
    {
        "id": "smoke-langsmith-1-escalada-cardio",
        "mensagem": "Estou com dor no peito irradiando para o braço esquerdo",
        "esperado": "intent=escalada, red_flag=cardiovascular, rule-based",
    },
    {
        "id": "smoke-langsmith-2-fora-escopo",
        "mensagem": "Qual o melhor investimento em ações para 2026?",
        "esperado": "intent=fora_de_escopo, sem chamadas LLM (rule-based)",
    },
    {
        "id": "smoke-langsmith-3-triagem-llm",
        "mensagem": "Estou com dor de cabeça leve desde ontem à tarde",
        "esperado": "intent=triagem, agente triagem com tool loop (chama LLM)",
    },
]


def main():
    console.print("[bold cyan]🔭 BluaDiagnostics — Smoke LangSmith (Dia 9)[/bold cyan]\n")

    # ============== 1. Verifica configuração ==============
    imprimir_status_startup()
    console.print()

    s = get_langsmith_status()
    if not s.enabled:
        console.print(
            Panel(
                "[red]LangSmith está desativado.[/red]\n\n"
                "Os traces NÃO serão enviados, mas o smoke vai rodar para validar\n"
                "que o grafo está funcionando. Configure o .env e rode de novo\n"
                "para ver os traces aparecerem no dashboard.",
                title="⚠️ Aviso",
                border_style="yellow",
            )
        )
        console.print()

    # ============== 2. Constrói grafo ==============
    console.print("[dim]Construindo grafo LangGraph...[/dim]")
    graph = build_graph()
    console.print("[green]✓ Grafo compilado[/green]\n")

    # ============== 3. Roda cenários ==============
    resultados = []
    for cenario in CENARIOS:
        console.print(
            Panel(
                f"[bold]{cenario['id']}[/bold]\n"
                f"[dim]Mensagem:[/dim] {cenario['mensagem']}\n"
                f"[dim]Esperado:[/dim] {cenario['esperado']}",
                border_style="blue",
            )
        )

        inicio = time.time()
        try:
            estado = invoke_with_message(
                graph=graph,
                user_message=cenario["mensagem"],
                thread_id=cenario["id"],
            )
            duracao = time.time() - inicio
            intent = estado.get("intent", "?")
            agentes = " → ".join(estado.get("agentes_acionados", []))
            console.print(
                f"  [green]✅[/green] intent=[cyan]{intent}[/cyan] · "
                f"trajetória=[magenta]{agentes}[/magenta] · "
                f"{duracao:.1f}s"
            )
            resultados.append({
                "id": cenario["id"],
                "ok": True,
                "intent": intent,
                "trajetoria": agentes,
                "duracao": duracao,
            })
        except Exception as exc:
            console.print(f"  [red]❌ ERRO: {type(exc).__name__}: {exc}[/red]")
            resultados.append({
                "id": cenario["id"],
                "ok": False,
                "intent": "ERROR",
                "trajetoria": "",
                "duracao": time.time() - inicio,
            })
        console.print()

    # ============== 4. Resumo ==============
    table = Table(title="Resumo", show_header=True, header_style="bold magenta")
    table.add_column("Cenário", style="cyan")
    table.add_column("Intent", justify="center")
    table.add_column("Trajetória")
    table.add_column("Duração", justify="right")
    table.add_column("Status", justify="center")

    for r in resultados:
        table.add_row(
            r["id"],
            r["intent"],
            r["trajetoria"],
            f"{r['duracao']:.1f}s",
            "[green]✅[/green]" if r["ok"] else "[red]❌[/red]",
        )
    console.print(table)

    # ============== 5. Instruções finais ==============
    hits = sum(1 for r in resultados if r["ok"])
    console.print()
    if s.enabled and hits == len(resultados):
        console.print(
            Panel(
                "[bold green]✅ Todos os cenários rodaram com sucesso.[/bold green]\n\n"
                f"Agora abra o dashboard do LangSmith:\n"
                f"  [cyan]https://smith.langchain.com/o/-/projects/p/{s.project}[/cyan]\n\n"
                "Você deve ver 3 novos traces aparecendo (1 por cenário).\n"
                "Para cada trace, expanda a árvore para ver:\n"
                "• Cada nó do grafo (supervisor → triagem/escalada/fora_escopo)\n"
                "• Chamadas LLM com tokens e latência\n"
                "• Tools chamadas\n"
                "• Inputs e outputs de cada etapa\n\n"
                "[dim italic]Dica: capture screenshots para o vídeo (Dia 11) e relatório (Dia 12).[/dim italic]",
                title="🎯 Próximo passo",
                border_style="green",
            )
        )
    elif not s.enabled:
        console.print(
            Panel(
                "[yellow]LangSmith desativado — traces não foram enviados.[/yellow]\n\n"
                "Configure as 3 env vars no .env e rode novamente:\n"
                "  LANGCHAIN_TRACING_V2=true\n"
                "  LANGCHAIN_API_KEY=ls__...\n"
                "  LANGCHAIN_PROJECT=bluadiagnostics-sprint2",
                title="⚠️ Ação necessária",
                border_style="yellow",
            )
        )
    else:
        console.print(
            Panel(
                f"[yellow]{hits}/{len(resultados)} cenários OK.[/yellow] "
                "Veja os erros acima.",
                title="⚠️ Verificar erros",
                border_style="yellow",
            )
        )


if __name__ == "__main__":
    main()
