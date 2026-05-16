"""
Smoke test do Dia 4a — tools + agente de escalada.

Valida que cada tool retorna dados sensatos e que o template de escalada
gera mensagens corretas para cada categoria de red flag.

Uso:
    python scripts/tools_smoke.py
"""
from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from src.agents.escalada import gerar_mensagem_escalada
from src.tools import (
    ALL_TOOLS,
    TOOLS_POR_AGENTE,
    dispatch_tool,
    get_tool_specs_for_agent,
    listar_tools_disponiveis,
)


console = Console()


def secao(titulo: str) -> None:
    console.print()
    console.print(Panel(f"[bold cyan]{titulo}[/bold cyan]", border_style="cyan"))


def imprimir_json(data: dict, titulo: str = "Resultado") -> None:
    """Imprime JSON formatado e colorido."""
    s = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    if len(s) > 800:
        s = s[:800] + "\n  ...[truncado]"
    syntax = Syntax(s, "json", theme="monokai", word_wrap=True)
    console.print(syntax)


# ============================================================
# Testes individuais
# ============================================================

def test_registry():
    secao("1. Registry — quais tools estão disponíveis?")
    tools = listar_tools_disponiveis()
    console.print(f"Total: [bold green]{len(tools)} tools[/bold green]")
    for t in tools:
        console.print(f"  • {t}")

    console.print("\n[bold]Tools por agente:[/bold]")
    for agente, tools_permitidas in TOOLS_POR_AGENTE.items():
        console.print(f"  • [cyan]{agente}[/cyan]: {len(tools_permitidas)} tools")


def test_consultar_historico():
    secao("2. consultar_historico_paciente — Maria (BNF-04821)")
    r = dispatch_tool("consultar_historico_paciente", {"paciente_id": "BNF-04821"})
    if r["status"] == "success":
        console.print(f"[green]✅ Paciente: {r['data']['nome_apelido']}, {r['data']['idade']}a[/green]")
        console.print(f"   Condições: {r['data']['condicoes_cronicas']}")
        console.print(f"   Alergias: {r['data']['alergias']}")
        console.print(f"   Medicação: {r['data']['medicamentos_em_uso'][0]['nome']} {r['data']['medicamentos_em_uso'][0]['dose']}")
    else:
        console.print(f"[red]❌ {r}[/red]")

    # Caso de erro — ID inválido
    console.print("\n[dim]Teste com ID inválido:[/dim]")
    r2 = dispatch_tool("consultar_historico_paciente", {"paciente_id": "XYZ-999"})
    console.print(f"   Status: {r2['status']} ({r2.get('mensagem', '')[:60]})")


def test_verificar_interacoes():
    secao("3. verificar_interacoes_medicamentosas — cenário canônico (Maria)")
    # Caso 1: ibuprofeno + losartana (interação conhecida)
    console.print("[bold]Caso 1: Maria toma Losartana e quer Ibuprofeno[/bold]")
    r = dispatch_tool("verificar_interacoes_medicamentosas", {
        "medicamentos": ["losartana", "ibuprofeno"],
        "paciente_id": "BNF-04821",
    })
    if r["status"] == "success":
        console.print(f"[green]✅ {r['total_interacoes']} interação(ões) encontrada(s)[/green]")
        for inter in r["interacoes_encontradas"]:
            console.print(f"   • {inter['par']} → [yellow]{inter['severidade']}[/yellow]")
            console.print(f"     {inter['mecanismo']}")

    # Caso 2: dipirona em paciente alérgico (Maria é alérgica)
    console.print("\n[bold]Caso 2: Dipirona em Maria (alérgica)[/bold]")
    r2 = dispatch_tool("verificar_interacoes_medicamentosas", {
        "medicamentos": ["dipirona"],
        "paciente_id": "BNF-04821",
    })
    if r2["contraindicacoes_alergia"]:
        console.print("[red]✅ Contraindicação detectada (esperado)[/red]")
        for ci in r2["contraindicacoes_alergia"]:
            console.print(f"   • {ci['medicamento']} → {ci['severidade']}")
            console.print(f"     {ci['recomendacao']}")
    else:
        console.print("[red]❌ ERRO: deveria detectar alergia a dipirona[/red]")


def test_agendar_teleconsulta():
    secao("4. agendar_teleconsulta — cardiologia urgente para Maria")
    r = dispatch_tool("agendar_teleconsulta", {
        "paciente_id": "BNF-04821",
        "especialidade": "cardiologia",
        "urgencia": "prioridade",
        "motivo_resumido": "Avaliação de controle pressórico e ajuste de medicação.",
    })
    if r["status"] == "success":
        console.print(f"[green]✅ Agendamento: {r['agendamento_id']}[/green]")
        console.print(f"   Profissional: {r['profissional']}")
        console.print(f"   Quando: {r['data_hora_humano']}")
        console.print(f"   Link: {r['link_video']}")
        console.print(f"   Preparação:")
        for inst in r["instrucoes_preparatorias"][:3]:
            console.print(f"     - {inst}")

    # Caso de erro — especialidade inválida
    console.print("\n[dim]Teste com especialidade inválida:[/dim]")
    r2 = dispatch_tool("agendar_teleconsulta", {
        "paciente_id": "BNF-04821",
        "especialidade": "neurocirurgia",  # não está nas 8
        "urgencia": "rotina",
        "motivo_resumido": "teste",
    })
    console.print(f"   Status: {r2['status']} ({r2.get('mensagem', '')[:80]})")


def test_wearables():
    secao("5. consultar_wearables (BÔNUS) — Maria com fadiga")
    r = dispatch_tool("consultar_wearables", {"paciente_id": "BNF-04821", "periodo_dias": 7})
    if r["status"] == "success":
        console.print(f"[green]✅ Dispositivo: {r['dispositivo']}[/green]")
        metr = r["metricas"]
        console.print(f"   FC repouso: {metr['frequencia_cardiaca']['repouso_bpm']} bpm")
        console.print(f"   PA estimada: {metr['pressao_arterial_estimada']['sistolica_media_mmhg']}/{metr['pressao_arterial_estimada']['diastolica_media_mmhg']}")
        console.print(f"   Sono média 7d: {metr['sono']['media_horas_7d']}h (qualidade {metr['sono']['qualidade_score_100']}/100)")
        console.print(f"   HRV: {metr['hrv_ms']['media_7d']}ms ({metr['hrv_ms']['tendencia']})")
        if metr.get("eventos_anormais"):
            for ev in metr["eventos_anormais"]:
                console.print(f"   ⚠ {ev['tipo']} em {ev['data']}: {ev['valor']}")


def test_escalada_templates():
    secao("6. agente de Escalada — templates por categoria")

    casos = [
        ("cardiovascular", "Maria", "dor no peito irradiando para o braço"),
        ("neurologica", "Maria", "perdi a força no lado esquerdo"),
        ("mental_grave", "Maria", "me machucar"),
        ("pediatrica", None, "manchas roxas com febre"),
    ]

    for categoria, nome, gatilho in casos:
        console.print(f"\n[bold cyan]Categoria: {categoria}[/bold cyan] (paciente: {nome or 'sem nome'})")
        msg = gerar_mensagem_escalada(categoria, nome, gatilho)
        console.print(Panel(msg, border_style="red", padding=(0, 1)))


def test_specs_para_agentes():
    secao("7. Tool specs disponíveis por agente")
    for agente in ["triagem", "prescricao", "escalada"]:
        specs = get_tool_specs_for_agent(agente)
        console.print(f"\n[cyan]{agente}[/cyan]: {len(specs)} tools")
        for s in specs:
            console.print(f"  • {s['name']}")


def main():
    console.print("[bold cyan]🩺 BluaDiagnostics — Dia 4a Smoke Test[/bold cyan]")
    console.print("[dim]Testando 5 tools + agente de escalada[/dim]")

    test_registry()
    test_consultar_historico()
    test_verificar_interacoes()
    test_agendar_teleconsulta()
    test_wearables()
    test_escalada_templates()
    test_specs_para_agentes()

    console.print()
    console.print("[bold green]✅ Dia 4a — tools e escalada validadas[/bold green]")
    console.print("[dim]Próximo: Dia 4b — agentes triagem + prescricao + builder do grafo[/dim]")


if __name__ == "__main__":
    main()
