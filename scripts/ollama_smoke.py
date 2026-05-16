"""
Smoke test comparativo — Groq vs Ollama (Dia 6).

Roda 4 cenários simples em AMBOS os providers e compara:
- Latência (segundos)
- Qualidade da resposta (snippet)
- Tokens consumidos

Cenários focam em casos SEM tool calling complexo (modelos 3B locais têm
qualidade variável em function calling).

⚠️ ESPERAR ~3-8 MINUTOS para o Ollama completar os 4 casos.
   Cada caso pode levar 30-90 segundos no T430u (inferência CPU).

Pré-requisitos:
- Groq: GROQ_API_KEY no .env
- Ollama: serviço rodando (`ollama serve` em background ou systemd)
- Modelo: ollama list deve mostrar llama3.2:3b

Uso:
    python scripts/ollama_smoke.py
    python scripts/ollama_smoke.py --so-ollama  # pula Groq
    python scripts/ollama_smoke.py --so-groq    # pula Ollama
"""
from __future__ import annotations

import argparse
import time
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.providers.llm_provider import get_provider, reset_provider_cache


console = Console()


# Cenários simples — sem tools — testam capacidade conversacional pura
CENARIOS = [
    {
        "id": "classificacao-intent",
        "descricao": "Classificação simples — supervisor-like",
        "system": (
            "Você é um classificador. Dada uma mensagem, responda APENAS com "
            "JSON: {\"intent\": \"triagem|prescricao|escalada|fora_de_escopo\"}. "
            "Sem texto extra."
        ),
        "user": "Estou com dor de cabeça leve desde ontem",
        "esperado_contem": ["triagem"],
    },
    {
        "id": "orientacao-clinica",
        "descricao": "Orientação clínica curta",
        "system": (
            "Você é um assistente de saúde da Care Plus. Tom acolhedor, frases "
            "curtas. Em até 4 frases, ajude o paciente."
        ),
        "user": "Estou com dor de cabeça. O que devo fazer?",
        "esperado_contem": ["água", "descanso", "médico", "consulta"],
    },
    {
        "id": "recusa-fora-escopo",
        "descricao": "Recusa educada de pergunta off-topic",
        "system": (
            "Você é um assistente de saúde da Care Plus. Recuse educadamente "
            "perguntas fora do escopo de saúde, redirecionando para o que sabe."
        ),
        "user": "Qual o melhor investimento em ações para 2026?",
        "esperado_contem": ["saúde", "ajudar", "sintomas", "Care"],
    },
    {
        "id": "resposta-curta-pt-br",
        "descricao": "Capacidade básica em PT-BR",
        "system": "Responda em português brasileiro, máximo 2 frases.",
        "user": "Qual a diferença entre paracetamol e ibuprofeno?",
        "esperado_contem": ["dor", "anti-inflamatório", "febre", "analgésico"],
    },
]


def rodar_caso(provider_name: str, cenario: dict) -> dict[str, Any]:
    """Roda um caso em um provider específico."""
    reset_provider_cache()
    provider = get_provider(force_provider=provider_name)

    messages = [
        {"role": "system", "content": cenario["system"]},
        {"role": "user", "content": cenario["user"]},
    ]

    inicio = time.time()
    try:
        response = provider.chat_completion(
            messages=messages,
            temperature=0.2,
            max_tokens=200,
        )
        duracao = time.time() - inicio

        # Avaliação simples: contém pelo menos uma palavra esperada?
        texto = response.text.lower()
        esperados = cenario.get("esperado_contem", [])
        match = any(e.lower() in texto for e in esperados) if esperados else True

        return {
            "ok": True,
            "match": match,
            "duracao_s": duracao,
            "resposta": response.text.strip(),
            "tokens": response.usage,
            "finish_reason": response.finish_reason,
        }
    except Exception as exc:
        return {
            "ok": False,
            "match": False,
            "duracao_s": time.time() - inicio,
            "erro": f"{type(exc).__name__}: {exc}",
            "resposta": "",
            "tokens": {"input_tokens": 0, "output_tokens": 0, "total": 0},
        }


def imprimir_caso(provider_name: str, cenario: dict, resultado: dict) -> None:
    cor = "yellow" if provider_name == "ollama" else "cyan"
    icon = "🦙" if provider_name == "ollama" else "⚡"

    status = ""
    if not resultado["ok"]:
        status = "[red]ERRO[/red]"
    elif resultado["match"]:
        status = "[green]✅ match[/green]"
    else:
        status = "[yellow]⚠️ sem match[/yellow]"

    console.print(
        f"\n  {icon} [{cor}]{provider_name.upper()}[/{cor}] "
        f"({resultado['duracao_s']:.1f}s) {status}"
    )
    if resultado["ok"]:
        resp = resultado["resposta"][:240] + ("..." if len(resultado["resposta"]) > 240 else "")
        console.print(f"     [dim]{resp}[/dim]")
        tokens = resultado["tokens"]
        console.print(
            f"     [dim italic]Tokens: in={tokens.get('input_tokens', 0)} "
            f"out={tokens.get('output_tokens', 0)} total={tokens.get('total', 0)}[/dim italic]"
        )
    else:
        console.print(f"     [red]{resultado.get('erro', '')[:200]}[/red]")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--so-ollama", action="store_true", help="Roda só com Ollama")
    parser.add_argument("--so-groq", action="store_true", help="Roda só com Groq")
    args = parser.parse_args()

    providers = []
    if not args.so_ollama:
        providers.append("groq")
    if not args.so_groq:
        providers.append("ollama")

    console.print("[bold cyan]🩺 BluaDiagnostics — Smoke Comparativo Groq vs Ollama (Dia 6)[/bold cyan]")
    console.print(
        f"[dim]Providers ativos: {', '.join(providers)} | "
        f"{len(CENARIOS)} cenários[/dim]"
    )
    console.print(
        "[dim italic]⚠️ Ollama em CPU pode levar 30-90s por caso. "
        "Total esperado: 3-8 min.[/dim italic]"
    )

    resultados: dict[str, list[dict]] = {p: [] for p in providers}

    for cenario in CENARIOS:
        console.print(
            Panel(
                f"[bold]{cenario['descricao']}[/bold]\n"
                f"[dim]System:[/dim] {cenario['system'][:90]}...\n"
                f"[dim]User:[/dim] {cenario['user']}",
                title=f"📋 {cenario['id']}",
                border_style="blue",
            )
        )

        for provider_name in providers:
            r = rodar_caso(provider_name, cenario)
            imprimir_caso(provider_name, cenario, r)
            resultados[provider_name].append(r)

    # ============== TABELA COMPARATIVA ==============
    console.print()
    table = Table(title="Comparativo Final", show_header=True, header_style="bold magenta")
    table.add_column("Cenário", style="cyan")
    for p in providers:
        table.add_column(f"{p}: latência", justify="right")
        table.add_column(f"{p}: match", justify="center")

    for i, cenario in enumerate(CENARIOS):
        row = [cenario["id"]]
        for p in providers:
            r = resultados[p][i]
            row.append(f"{r['duracao_s']:.1f}s")
            if not r["ok"]:
                row.append("[red]ERR[/red]")
            elif r["match"]:
                row.append("[green]✅[/green]")
            else:
                row.append("[yellow]⚠️[/yellow]")
        table.add_row(*row)

    console.print(table)

    # ============== RESUMO LGPD ==============
    console.print()
    console.print(
        Panel(
            "[bold yellow]🔒 Justificativa LGPD para Ollama Local[/bold yellow]\n\n"
            "Em contexto Care Plus / dados de saúde sensíveis (Art. 5º, II LGPD), "
            "rodar o LLM 100% on-premise via Ollama:\n"
            "• Elimina trânsito de PHI para servidores de terceiros\n"
            "• Habilita compliance com normas hospitalares (Wi-Fi controlado)\n"
            "• Atende princípio de minimização de dados (Art. 6º, III)\n\n"
            "[dim]Trade-off: latência 10-30x maior em CPU. Em produção, "
            "Groq como default + Ollama opcional para tenants corporate "
            "com exigência regulatória.[/dim]",
            border_style="yellow",
        )
    )


if __name__ == "__main__":
    main()
