"""Tradutor: BluaState (estado real do grafo) -> contrato JSON do handover.

O handover especificou um contrato idealizado. O BluaState real usa nomes e
estruturas diferentes. Esta camada reconcilia os dois — e e a unica peca que
conhece os dois formatos, isolando o app das particularidades internas da IA.
"""
from __future__ import annotations

from typing import Any

from app.api.sugestao_parser import extrair_sugestao


def _ultima_resposta_assistant(mensagens: list[dict[str, Any]]) -> str:
    """Pega o conteudo da ultima mensagem do assistente (igual ao Streamlit)."""
    for msg in reversed(mensagens or []):
        if msg.get("role") == "assistant":
            return msg.get("content", "") or ""
    return ""


def _nomes_das_tools(tools_chamadas: list[dict[str, Any]]) -> list[str]:
    """Contrato pede lista de nomes; o state guarda objetos ToolCallRecord."""
    nomes: list[str] = []
    for tc in tools_chamadas or []:
        nome = tc.get("nome")
        if nome and nome not in nomes:
            nomes.append(nome)
    return nomes


def _nomes_dos_docs(docs_recuperados: list[dict[str, Any]]) -> list[str]:
    """Contrato pede identificadores de documento; state guarda DocRecuperado."""
    nomes: list[str] = []
    for doc in docs_recuperados or []:
        ident = doc.get("source_file") or doc.get("kb_id")
        if ident and ident not in nomes:
            nomes.append(ident)
    return nomes


def traduzir_estado_para_contrato(
    estado_final: dict[str, Any],
    thread_id: str,
) -> dict[str, Any]:
    """Converte o BluaState retornado por graph.invoke() no objeto do contrato."""
    texto_bruto = _ultima_resposta_assistant(estado_final.get("mensagens", []))
    texto_limpo, sugestao = extrair_sugestao(texto_bruto)
    intent = estado_final.get("intent")

    # Fallback: se a resposta ficou vazia mas ha sugestao de prescricao
    # (todo o conteudo estava no bloco <sugestao>), o paciente nao pode ver
    # um balao vazio. Damos um texto neutro — o detalhe vai para o medico.
    if not texto_limpo and sugestao is not None:
        texto_limpo = (
            "Sua solicitacao foi registrada e encaminhada para revisao medica."
        )

    # red_flags: o state guarda objetos ricos (RedFlagInfo). O contrato trata
    # "nao-vazio" como sinal de emergencia, entao preservamos os objetos —
    # o app so checa .length para o banner, e o medico pode ver o detalhe.
    #
    # IMPORTANTE para o time do app: EMERGENCIA = red_flags nao-vazio.
    # NAO confundir com requer_escalada_humana, que tambem fica true em
    # prescricao (toda prescricao vai para revisao medica = escalada).
    # Banner de emergencia (SAMU/CVV) so quando red_flags tem item.
    red_flags = estado_final.get("red_flags_detectadas", []) or []

    return {
        "resposta": texto_limpo,
        "intent": intent,
        "requer_escalada_humana": bool(
            estado_final.get("requer_escalada_humana", False)
        ),
        "red_flags": red_flags,
        # sugestao_prescricao so faz sentido quando intent == "prescricao".
        "sugestao_prescricao": sugestao if intent == "prescricao" else None,
        "tools_usadas": _nomes_das_tools(estado_final.get("tools_chamadas", [])),
        "docs_consultados": _nomes_dos_docs(estado_final.get("docs_recuperados", [])),
        "thread_id": thread_id,
    }
