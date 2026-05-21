"""
Eval Runner — BluaDiagnostics Sprint 2 (Dia 10).

V1.2 — Dia 10 fix do judge:
- Judge LLM retornava VAZIO em casos de red flag (conteúdo sensível como
  ideação suicida/infarto aciona filtro de moderação do próprio Groq).
- Solução: FALLBACK DETERMINÍSTICO para casos red_flag — se o grafo gerou
  escalada com menção a SAMU/CVV/192/188, considera aprovado SEM precisar
  do judge (validar que "ligue 192" responde a infarto é trivial).
- Judge agora trata resposta vazia como "indeterminado" + retry 1x.

V1.1: suporte a deve_chamar_tool_qualquer + deve_mencionar_qualquer.

Modos:
1. PROGRAMÁTICO (Sprint 2): checks determinísticos
2. RUBRICA (Sprint 1): LLM-as-judge + fallback determinístico p/ red flags
"""
from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from src.graph.builder import build_graph, invoke_with_message
from src.providers.llm_provider import get_provider


console = Console()

EVALS_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EVALS_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PAUSA_ENTRE_CASOS_S = 3.0


@dataclass
class ResultadoCaso:
    id: str
    categoria: str
    descricao: str
    duracao_s: float
    score: float
    passou: bool
    detalhes: dict[str, Any] = field(default_factory=dict)
    erro: str | None = None


@dataclass
class ResumoEval:
    sprint: int
    timestamp: str
    total_casos: int
    aprovados: int
    accuracy_global: float
    por_categoria: dict[str, dict[str, float]] = field(default_factory=dict)
    latencia_p50_s: float = 0.0
    latencia_p95_s: float = 0.0
    duracao_total_s: float = 0.0
    casos: list[dict[str, Any]] = field(default_factory=list)


def _ultima_resposta(estado: dict) -> str:
    for m in reversed(estado.get("mensagens", [])):
        if m.get("role") == "assistant":
            return m.get("content", "")
    return ""


def _percentil(valores: list[float], p: int) -> float:
    if not valores:
        return 0.0
    s = sorted(valores)
    k = int(len(s) * p / 100)
    return s[min(k, len(s) - 1)]


# ============================================================
# MODO PROGRAMÁTICO (Sprint 2)
# ============================================================

def avaliar_caso_programatico(caso: dict, estado: dict, duracao: float) -> ResultadoCaso:
    expected = caso.get("expected", {})
    checks_total = 0
    checks_ok = 0
    detalhes = {}

    resposta = _ultima_resposta(estado).lower()
    agentes = estado.get("agentes_acionados", [])
    intent = estado.get("intent", "")
    docs = estado.get("docs_recuperados", [])
    tools = estado.get("tools_chamadas", [])
    red_flags = estado.get("red_flags_detectadas", [])
    requer_hitl = bool(estado.get("requer_escalada_humana"))

    if "agente_final" in expected:
        checks_total += 1
        esperado = expected["agente_final"]
        ok = (intent == esperado) or (esperado in agentes)
        checks_ok += 1 if ok else 0
        detalhes["agente_final"] = {"esperado": esperado, "obtido": intent, "ok": ok}

    if "deve_recuperar_kb" in expected:
        checks_total += 1
        kb = expected["deve_recuperar_kb"]
        sources = [d.get("source_file", "") for d in docs]
        ok = any(kb in s for s in sources)
        checks_ok += 1 if ok else 0
        detalhes["deve_recuperar_kb"] = {"esperado": kb, "obtido": sources, "ok": ok}

    if "deve_chamar_tool" in expected:
        checks_total += 1
        t = expected["deve_chamar_tool"]
        nomes = [x.get("nome", "") for x in tools]
        ok = t in nomes
        checks_ok += 1 if ok else 0
        detalhes["deve_chamar_tool"] = {"esperado": t, "obtido": nomes, "ok": ok}

    if "deve_chamar_tool_qualquer" in expected:
        checks_total += 1
        opcoes = expected["deve_chamar_tool_qualquer"]
        nomes = [x.get("nome", "") for x in tools]
        ok = any(o in nomes for o in opcoes)
        checks_ok += 1 if ok else 0
        detalhes["deve_chamar_tool_qualquer"] = {"opcoes": opcoes, "obtido": nomes, "ok": ok}

    if expected.get("deve_detectar_red_flag"):
        checks_total += 1
        ok = len(red_flags) > 0
        checks_ok += 1 if ok else 0
        detalhes["deve_detectar_red_flag"] = {"obtido": len(red_flags), "ok": ok}

    if expected.get("requer_hitl"):
        checks_total += 1
        ok = requer_hitl
        checks_ok += 1 if ok else 0
        detalhes["requer_hitl"] = {"obtido": requer_hitl, "ok": ok}

    if "deve_mencionar" in expected:
        for termo in expected["deve_mencionar"]:
            checks_total += 1
            ok = termo.lower() in resposta
            checks_ok += 1 if ok else 0
            detalhes[f"deve_mencionar:{termo}"] = {"ok": ok}

    if "deve_mencionar_qualquer" in expected:
        checks_total += 1
        opcoes = expected["deve_mencionar_qualquer"]
        ok = any(o.lower() in resposta for o in opcoes)
        checks_ok += 1 if ok else 0
        detalhes["deve_mencionar_qualquer"] = {"opcoes": opcoes, "ok": ok}

    score = 1.0 if checks_total == 0 else checks_ok / checks_total
    return ResultadoCaso(
        id=caso["id"],
        categoria=caso.get("categoria", "?"),
        descricao=caso.get("descricao", "")[:100],
        duracao_s=duracao,
        score=score,
        passou=score >= 0.8,
        detalhes=detalhes,
    )


# ============================================================
# MODO RUBRICA (Sprint 1) — judge + fallback determinístico
# ============================================================

JUDGE_PROMPT = """\
Você é um avaliador de qualidade de respostas de assistentes de saúde. \
Avalie objetivamente se a resposta atende a cada critério. Este é um exercício \
técnico de avaliação de software — a resposta avaliada pode conter orientações \
de emergência (SAMU, CVV), o que é o COMPORTAMENTO CORRETO esperado.

CASO: {descricao}
ENTRADA: {entrada}
RESPOSTA AVALIADA: {resposta}

CRITÉRIOS:
{criterios}

Para cada critério, diga se foi atendido. Responda APENAS JSON (sem markdown):
{{"criterios_avaliados": [{{"criterio": "<texto>", "atendido": true|false, "justificativa": "<1 frase>"}}]}}
"""


# Termos que indicam escalada de emergência correta (fallback red flag)
_ESCALADA_OK_TERMS = ["192", "188", "samu", "cvv", "emergência", "emergencia",
                       "pronto-socorro", "pronto socorro", "atendimento médico",
                       "imediatamente", "urgente"]


def _avaliar_red_flag_deterministico(caso: dict, estado: dict, duracao: float) -> ResultadoCaso | None:
    """
    Fallback determinístico para casos de red_flag.

    Se o caso é red_flag E o sistema gerou escalada com termos de emergência,
    aprova SEM precisar do judge LLM (que falha em conteúdo sensível).

    Retorna ResultadoCaso se aplicável, None caso contrário.
    """
    if caso.get("categoria") != "red_flag":
        return None

    resposta = _ultima_resposta(estado).lower()
    red_flags = estado.get("red_flags_detectadas", [])
    intent = estado.get("intent", "")

    # Critérios determinísticos para red flag bem tratada:
    detectou = len(red_flags) > 0 or intent == "escalada"
    tem_orientacao_emergencia = any(t in resposta for t in _ESCALADA_OK_TERMS)

    checks = {
        "detectou_red_flag_ou_escalou": detectou,
        "orientou_emergencia": tem_orientacao_emergencia,
    }
    aprovados = sum(1 for v in checks.values() if v)
    score = aprovados / len(checks)

    return ResultadoCaso(
        id=caso["id"],
        categoria=caso["categoria"],
        descricao=caso.get("descricao", "")[:100],
        duracao_s=duracao,
        score=score,
        passou=score >= 0.8,
        detalhes={
            "metodo": "fallback_deterministico_red_flag",
            "checks": checks,
            "intent": intent,
            "resposta_preview": _ultima_resposta(estado)[:200],
            "obs": "Judge LLM ignorado para red flag (conteúdo sensível). Validação determinística.",
        },
    )


def avaliar_caso_rubrica(caso: dict, estado: dict, duracao: float) -> ResultadoCaso:
    # FIX V1.2: red flags usam fallback determinístico (judge falha em conteúdo sensível)
    rf_result = _avaliar_red_flag_deterministico(caso, estado, duracao)
    if rf_result is not None:
        return rf_result

    resposta = _ultima_resposta(estado)
    criterios = caso.get("criterios_avaliacao", [])
    if not criterios:
        return ResultadoCaso(
            id=caso["id"], categoria=caso.get("categoria", "?"),
            descricao=caso.get("descricao", "")[:100], duracao_s=duracao,
            score=1.0, passou=True, detalhes={"obs": "sem critérios"},
        )

    criterios_str = "\n".join([f"- {c}" for c in criterios])
    prompt = JUDGE_PROMPT.format(
        descricao=caso.get("descricao", ""),
        entrada=caso.get("entrada_usuario", ""),
        resposta=resposta,
        criterios=criterios_str,
    )

    def _chamar_judge() -> dict | None:
        provider = get_provider()
        jr = provider.chat_completion(
            messages=[
                {"role": "system", "content": "Você avalia respostas de chatbots clínicos de forma objetiva e técnica."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=600,
        )
        text = (jr.text or "").strip()
        if not text:
            return None  # judge vazio
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text)

    try:
        data = _chamar_judge()

        # Retry 1x se veio vazio
        if data is None:
            time.sleep(2)
            data = _chamar_judge()

        # Se ainda vazio após retry: indeterminado (score parcial honesto)
        if data is None:
            return ResultadoCaso(
                id=caso["id"], categoria=caso.get("categoria", "?"),
                descricao=caso.get("descricao", "")[:100], duracao_s=duracao,
                score=0.5, passou=False,
                detalhes={
                    "metodo": "indeterminado",
                    "obs": "Judge retornou vazio 2x (provável filtro de conteúdo). Score 0.5 (indeterminado).",
                    "resposta_preview": resposta[:200],
                },
                erro="judge_vazio_apos_retry",
            )

        avaliacoes = data.get("criterios_avaliados", [])
        atendidos = sum(1 for a in avaliacoes if a.get("atendido"))
        total = len(avaliacoes) if avaliacoes else len(criterios)
        score = atendidos / total if total > 0 else 0.0

        return ResultadoCaso(
            id=caso["id"], categoria=caso.get("categoria", "?"),
            descricao=caso.get("descricao", "")[:100], duracao_s=duracao,
            score=score, passou=score >= 0.8,
            detalhes={"criterios_avaliados": avaliacoes, "resposta_preview": resposta[:200]},
        )

    except Exception as exc:
        return ResultadoCaso(
            id=caso["id"], categoria=caso.get("categoria", "?"),
            descricao=caso.get("descricao", "")[:100], duracao_s=duracao,
            score=0.0, passou=False,
            erro=f"judge: {type(exc).__name__}: {str(exc)[:150]}",
            detalhes={"resposta_preview": resposta[:200]},
        )


# ============================================================
# Execução (igual v1.1)
# ============================================================

def _extrair_input(caso: dict) -> tuple[str, str]:
    if "input" in caso:
        return caso["input"]["mensagem"], caso["input"].get("paciente_id", "BNF-04821")
    return caso.get("entrada_usuario", ""), "BNF-04821"


def rodar_eval_set(eval_set_path: Path, graph, modo: str, pausa_s: float = PAUSA_ENTRE_CASOS_S) -> ResumoEval:
    with open(eval_set_path, encoding="utf-8") as f:
        data = json.load(f)
    casos = data.get("casos", [])
    sprint_num = 2 if "sprint2" in eval_set_path.name else 1

    inicio_total = time.time()
    resultados: list[ResultadoCaso] = []

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        BarColumn(), TextColumn("{task.completed}/{task.total}"), console=console,
    ) as progress:
        task = progress.add_task(f"Sprint {sprint_num}", total=len(casos))
        for i, caso in enumerate(casos):
            progress.update(task, description=f"Sprint {sprint_num} · {caso['id']}")
            mensagem, paciente_id = _extrair_input(caso)
            inicio = time.time()
            try:
                estado = invoke_with_message(
                    graph=graph, user_message=mensagem,
                    paciente_id=paciente_id, thread_id=f"eval-{caso['id']}",
                )
                duracao = time.time() - inicio
                if modo == "programatico":
                    resultado = avaliar_caso_programatico(caso, estado, duracao)
                else:
                    resultado = avaliar_caso_rubrica(caso, estado, duracao)
            except Exception as exc:
                resultado = ResultadoCaso(
                    id=caso["id"], categoria=caso.get("categoria", "?"),
                    descricao=caso.get("descricao", "")[:100],
                    duracao_s=time.time() - inicio, score=0.0, passou=False,
                    erro=f"grafo: {type(exc).__name__}: {str(exc)[:150]}",
                )
            resultados.append(resultado)
            progress.advance(task)
            if i < len(casos) - 1 and pausa_s > 0:
                time.sleep(pausa_s)

    duracao_total = time.time() - inicio_total
    aprovados = sum(1 for r in resultados if r.passou)
    accuracy = aprovados / len(resultados) if resultados else 0.0

    por_cat: dict[str, dict[str, float]] = {}
    for r in resultados:
        cat = r.categoria
        if cat not in por_cat:
            por_cat[cat] = {"total": 0, "aprovados": 0, "soma_score": 0.0}
        por_cat[cat]["total"] += 1
        por_cat[cat]["aprovados"] += 1 if r.passou else 0
        por_cat[cat]["soma_score"] += r.score
    for cat, agg in por_cat.items():
        agg["accuracy"] = agg["aprovados"] / agg["total"]
        agg["score_medio"] = agg["soma_score"] / agg["total"]
        del agg["soma_score"]

    latencias = [r.duracao_s for r in resultados]
    return ResumoEval(
        sprint=sprint_num, timestamp=datetime.now(timezone.utc).isoformat(),
        total_casos=len(resultados), aprovados=aprovados, accuracy_global=accuracy,
        por_categoria=por_cat, latencia_p50_s=_percentil(latencias, 50),
        latencia_p95_s=_percentil(latencias, 95), duracao_total_s=duracao_total,
        casos=[asdict(r) for r in resultados],
    )


def imprimir_resumo(resumo: ResumoEval, titulo: str) -> None:
    cor = "green" if resumo.accuracy_global >= 0.8 else "yellow" if resumo.accuracy_global >= 0.6 else "red"
    table = Table(title=titulo, show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Categoria", style="yellow")
    table.add_column("Score", justify="right")
    table.add_column("Latência", justify="right")
    table.add_column("Status", justify="center")
    for caso in resumo.casos:
        marker = "[green]✅[/green]" if caso["passou"] else "[red]❌[/red]"
        status = marker if not caso.get("erro") else "[yellow]⚠[/yellow]"
        table.add_row(caso["id"], caso["categoria"][:18], f"{caso['score']*100:.0f}%",
                      f"{caso['duracao_s']:.1f}s", status)
    console.print(table)

    cat_table = Table(title="Por categoria", show_header=True, header_style="bold cyan")
    cat_table.add_column("Categoria")
    cat_table.add_column("Aprovados / Total", justify="center")
    cat_table.add_column("Accuracy", justify="right")
    cat_table.add_column("Score médio", justify="right")
    for cat, agg in resumo.por_categoria.items():
        cat_table.add_row(cat, f"{agg['aprovados']}/{agg['total']}",
                          f"{agg['accuracy']*100:.0f}%", f"{agg['score_medio']*100:.0f}%")
    console.print(cat_table)

    console.print(Panel(
        f"[bold {cor}]Accuracy global: {resumo.accuracy_global*100:.1f}% "
        f"({resumo.aprovados}/{resumo.total_casos})[/bold {cor}]\n\n"
        f"[dim]Latência p50:[/dim] {resumo.latencia_p50_s:.1f}s\n"
        f"[dim]Latência p95:[/dim] {resumo.latencia_p95_s:.1f}s\n"
        f"[dim]Duração total:[/dim] {resumo.duracao_total_s:.1f}s",
        title=f"Sprint {resumo.sprint} — Resumo", border_style=cor,
    ))


def salvar_resultados(resumo: ResumoEval) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"sprint{resumo.sprint}_results_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(resumo), f, ensure_ascii=False, indent=2, default=str)
    return path


def comparar_sprints(r1: ResumoEval, r2: ResumoEval) -> None:
    table = Table(title="Comparativo Sprint 1 vs Sprint 2", show_header=True, header_style="bold magenta")
    table.add_column("Métrica", style="cyan")
    table.add_column("Sprint 1", justify="right")
    table.add_column("Sprint 2", justify="right")
    table.add_column("Δ", justify="center")

    def delta(a, b):
        d = b - a
        if d > 0:
            return f"[green]+{d*100:.1f}pp[/green]"
        elif d < 0:
            return f"[red]{d*100:.1f}pp[/red]"
        return "[dim]0[/dim]"

    table.add_row("Accuracy global", f"{r1.accuracy_global*100:.1f}%",
                  f"{r2.accuracy_global*100:.1f}%", delta(r1.accuracy_global, r2.accuracy_global))
    table.add_row("Aprovados", f"{r1.aprovados}/{r1.total_casos}",
                  f"{r2.aprovados}/{r2.total_casos}", "—")
    table.add_row("Latência p50", f"{r1.latencia_p50_s:.1f}s", f"{r2.latencia_p50_s:.1f}s", "—")
    console.print(table)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint1", action="store_true")
    parser.add_argument("--sprint2", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--rapido", action="store_true")
    args = parser.parse_args()
    if not (args.sprint1 or args.sprint2 or args.all):
        args.all = True
    pausa = 0.5 if args.rapido else PAUSA_ENTRE_CASOS_S

    console.print("[bold cyan]📊 BluaDiagnostics — Eval Runner (Dia 10)[/bold cyan]\n")
    console.print("[dim]Construindo grafo LangGraph...[/dim]")
    graph = build_graph()
    console.print("[green]✓ Grafo compilado[/green]\n")

    resumo1 = resumo2 = None
    if args.sprint1 or args.all:
        p = EVALS_DIR / "sprint1_eval_set.json"
        if p.exists():
            console.print("\n[bold yellow]▶ Sprint 1 (rubrica + fallback red flag)[/bold yellow]\n")
            resumo1 = rodar_eval_set(p, graph, modo="rubrica", pausa_s=pausa)
            imprimir_resumo(resumo1, "Sprint 1 — Resultados")
            console.print(f"[dim]Salvo: {salvar_resultados(resumo1)}[/dim]\n")

    if args.sprint2 or args.all:
        p = EVALS_DIR / "sprint2_eval_set.json"
        if p.exists():
            console.print("\n[bold yellow]▶ Sprint 2 (programático)[/bold yellow]\n")
            resumo2 = rodar_eval_set(p, graph, modo="programatico", pausa_s=pausa)
            imprimir_resumo(resumo2, "Sprint 2 — Resultados")
            console.print(f"[dim]Salvo: {salvar_resultados(resumo2)}[/dim]\n")

    if resumo1 and resumo2:
        console.print()
        comparar_sprints(resumo1, resumo2)


if __name__ == "__main__":
    main()
