"""
Smoke test do Supervisor.

Valida que a classificação de intent funciona corretamente para casos
representativos das 4 categorias + casos críticos de red flag.

Roda 15 casos:
- 4 red flags (devem virar "escalada" via guardrail)
- 3 prescricao (rule-based)
- 3 triagem (rule-based)
- 1 escalada explícita (rule-based)
- 2 fora_de_escopo (rule-based em scope.py)
- 2 ambíguos (vão para LLM fallback)

Pré-requisito:
- GROQ_API_KEY no .env (pra rodar os 2 ambíguos)
- venv ativada

Uso:
    python scripts/supervisor_smoke.py
    python scripts/supervisor_smoke.py "mensagem custom"
"""
from __future__ import annotations

import sys

from rich.console import Console
from rich.table import Table

from src.agents.supervisor import classificar


console = Console()


# Casos de teste: (mensagem, intent_esperado, descrição)
CASOS_TESTE = [
    # ---- Red flags (devem virar "escalada" via guardrail, fonte=regra) ----
    (
        "Estou com dor no peito que está irradiando para o braço esquerdo, com muito suor frio",
        "escalada",
        "🚨 IAM clássico — cardiovascular",
    ),
    (
        "Acho que estou tendo um derrame, perdi a força no lado esquerdo",
        "escalada",
        "🚨 AVC — neurológico",
    ),
    (
        "Estou com pensamentos de me machucar, não quero mais viver",
        "escalada",
        "🚨 Ideação suicida — mental_grave",
    ),
    (
        "Minha filha de 8 meses está com febre alta e umas manchas roxas na perna",
        "escalada",
        "🚨 Pediátrica — petéquias com febre",
    ),

    # ---- Prescrição (rule-based) ----
    (
        "Doutor, pode me passar uma receita de antibiótico?",
        "prescricao",
        "Pedido explícito de antibiótico",
    ),
    (
        "Preciso renovar a receita da minha Losartana",
        "prescricao",
        "Renovação de prescrição contínua",
    ),
    (
        "Me prescreva algo para essa dor lombar",
        "prescricao",
        "Pedido explícito de prescrição",
    ),

    # ---- Triagem (rule-based) ----
    (
        "Estou com dor de cabeça leve desde ontem à tarde",
        "triagem",
        "Sintoma leve — autoavaliação",
    ),
    (
        "Posso tomar ibuprofeno se eu uso Losartana?",
        "triagem",
        "Dúvida sobre interação (não pedido de receita)",
    ),
    (
        "Tenho febre há 3 dias e tosse seca",
        "triagem",
        "Sintomas com duração",
    ),

    # ---- Escalada explícita (sem red flag clínica, mas pedido humano) ----
    (
        "Quero falar com um médico humano agora",
        "escalada",
        "Pedido explícito de humano",
    ),

    # ---- Fora de escopo (rule-based em scope.py) ----
    (
        "Qual o melhor investimento em ações para 2026?",
        "fora_de_escopo",
        "Pergunta sobre finanças",
    ),
    (
        "Você sabe a previsão do tempo para amanhã?",
        "fora_de_escopo",
        "Pergunta sobre clima",
    ),

    # ---- Ambíguos (vão para LLM fallback) ----
    (
        "Acordei mal hoje, não sei explicar direito",
        "triagem",
        "Vago — LLM provavelmente classifica como triagem",
    ),
    (
        "Preciso de ajuda urgente com a minha mãe",
        "escalada",
        "Pode ser red flag implícita ou pedido de humano — LLM decide",
    ),
]


def run_one(mensagem: str, esperado: str | None = None, descricao: str = "") -> bool:
    """Roda um caso e imprime resultado. Retorna True se match."""
    resultado = classificar(mensagem)
    intent = resultado["intent"]
    motivo = resultado["motivo"]
    red_flags = resultado["red_flags"]

    match = (esperado is None) or (intent == esperado)
    marker = "[green]✅[/green]" if match else "[red]❌[/red]"

    console.print(
        f"{marker} [cyan]{intent}[/cyan]  "
        f"[dim](esperado: {esperado or '?'})[/dim]"
    )
    if descricao:
        console.print(f"   [dim italic]→ {descricao}[/dim italic]")
    console.print(f"   [yellow]Msg:[/yellow] {mensagem[:90]}{'...' if len(mensagem)>90 else ''}")
    console.print(f"   [magenta]Motivo:[/magenta] {motivo}")
    if red_flags:
        for rf in red_flags:
            console.print(f"   [red]RF:[/red] {rf['categoria']} ({rf['severidade']}) — gatilho: '{rf['frase_gatilho']}'")
    console.print()
    return match


def main() -> None:
    # Custom query
    if len(sys.argv) > 1:
        custom = " ".join(sys.argv[1:])
        console.print(f"[bold cyan]Query custom:[/bold cyan] {custom}\n")
        run_one(custom, esperado=None, descricao="modo custom")
        return

    console.print("[bold cyan]🩺 BluaDiagnostics — Supervisor Smoke Test[/bold cyan]")
    console.print(f"[dim]Rodando {len(CASOS_TESTE)} casos[/dim]")
    console.print()

    hits = 0
    for msg, esperado, desc in CASOS_TESTE:
        if run_one(msg, esperado, desc):
            hits += 1

    # Resumo
    pct = (hits / len(CASOS_TESTE)) * 100
    color = "green" if pct >= 80 else "yellow" if pct >= 60 else "red"

    table = Table(title="Resumo Final", show_header=True, header_style="bold magenta")
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", justify="right")
    table.add_row("Total de casos", str(len(CASOS_TESTE)))
    table.add_row("Acertos", str(hits))
    table.add_row("Acurácia", f"{pct:.1f}%")
    console.print(table)

    console.print()
    if pct >= 80:
        console.print(f"[bold green]✅ Supervisor saudável ({pct:.0f}%)[/bold green]")
    elif pct >= 60:
        console.print(f"[bold yellow]⚠ Supervisor aceitável mas precisa iterar ({pct:.0f}%)[/bold yellow]")
    else:
        console.print(f"[bold red]❌ Supervisor precisa de ajustes ({pct:.0f}%)[/bold red]")


if __name__ == "__main__":
    main()
