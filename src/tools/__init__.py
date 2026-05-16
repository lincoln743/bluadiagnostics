"""
Registry central das tools — ponto único de acesso para os agentes.

Vantagens:
- Os agentes não importam cada tool individualmente — pedem por nome.
- Adicionar tool nova = adicionar uma linha em ALL_TOOLS.
- Dispatch unificado: agente recebe (nome, args) e o registry chama a função certa.

Uso pelos agentes:
    from src.tools import get_tool_specs_for_agent, dispatch_tool

    # 1. Pegar specs para passar para o LLM (formato Anthropic)
    specs = get_tool_specs_for_agent("triagem")

    # 2. Quando o LLM chamar uma tool, dispatch:
    result = dispatch_tool("consultar_historico_paciente", {"paciente_id": "BNF-04821"})
"""
from __future__ import annotations

import json
from typing import Any, Callable

from src.tools.agendar_teleconsulta import (
    TOOL_SPEC as AGENDAR_SPEC,
    agendar_teleconsulta,
)
from src.tools.buscar_conhecimento import (
    TOOL_SPEC as BUSCAR_SPEC,
    buscar_conhecimento_clinico,
)
from src.tools.consultar_historico import (
    TOOL_SPEC as HISTORICO_SPEC,
    consultar_historico_paciente,
)
from src.tools.consultar_wearables import (
    TOOL_SPEC as WEARABLES_SPEC,
    consultar_wearables,
)
from src.tools.verificar_interacoes import (
    TOOL_SPEC as INTERACOES_SPEC,
    verificar_interacoes_medicamentosas,
)


# ============================================================
# Registry: nome → (spec, função)
# ============================================================

ALL_TOOLS: dict[str, tuple[dict[str, Any], Callable]] = {
    "consultar_historico_paciente":    (HISTORICO_SPEC, consultar_historico_paciente),
    "verificar_interacoes_medicamentosas": (INTERACOES_SPEC, verificar_interacoes_medicamentosas),
    "agendar_teleconsulta":            (AGENDAR_SPEC, agendar_teleconsulta),
    "consultar_wearables":             (WEARABLES_SPEC, consultar_wearables),
    "buscar_conhecimento_clinico":     (BUSCAR_SPEC, buscar_conhecimento_clinico),
}


# ============================================================
# Quais tools cada agente pode usar (defesa em profundidade)
# ============================================================

TOOLS_POR_AGENTE: dict[str, list[str]] = {
    "triagem": [
        "consultar_historico_paciente",
        "buscar_conhecimento_clinico",
        "consultar_wearables",
        "agendar_teleconsulta",
    ],
    "prescricao": [
        "consultar_historico_paciente",
        "verificar_interacoes_medicamentosas",
        "buscar_conhecimento_clinico",
        "agendar_teleconsulta",  # pode encaminhar para teleconsulta como alternativa
    ],
    "escalada": [],   # zero tools — agente determinístico
    "supervisor": [], # zero tools — só classifica
}


# ============================================================
# API pública
# ============================================================

def get_tool_specs_for_agent(agent_name: str) -> list[dict[str, Any]]:
    """
    Retorna lista de tool specs (formato Anthropic) que o agente pode usar.
    Vazio se o agente não usa tools (escalada, supervisor).
    """
    permitidas = TOOLS_POR_AGENTE.get(agent_name, [])
    return [ALL_TOOLS[nome][0] for nome in permitidas if nome in ALL_TOOLS]


def dispatch_tool(nome: str, args: dict[str, Any] | str) -> dict[str, Any]:
    """
    Executa a tool por nome. Aceita args como dict OU string JSON
    (Groq retorna string JSON nos tool_calls).

    Returns:
        Dict com resultado da tool, ou dict de erro padronizado.
    """
    if nome not in ALL_TOOLS:
        return {
            "status": "error",
            "mensagem": f"Tool desconhecida: '{nome}'. Disponíveis: {list(ALL_TOOLS.keys())}",
        }

    # Parse args se for string
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError as exc:
            return {
                "status": "error",
                "mensagem": f"Argumentos inválidos (não é JSON): {exc}",
                "args_recebidos": args,
            }

    _, func = ALL_TOOLS[nome]

    try:
        return func(**args)
    except TypeError as exc:
        # Argumentos errados (campo faltando, tipo errado)
        return {
            "status": "error",
            "mensagem": f"Erro ao chamar {nome}: {exc}",
            "args_recebidos": args,
        }
    except Exception as exc:
        # Qualquer outro erro inesperado da tool
        return {
            "status": "error",
            "mensagem": f"Exceção em {nome}: {type(exc).__name__}: {exc}",
            "args_recebidos": args,
        }


def listar_tools_disponiveis() -> list[str]:
    """Helper para introspecção/debug."""
    return list(ALL_TOOLS.keys())
