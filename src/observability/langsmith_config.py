"""
LangSmith config helper — v1.1 (Dia 9 fix).

CHANGELOG v1.0 → v1.1:
- Chama load_dotenv() no import para garantir que .env seja lido
  mesmo quando chamado via `python -c "..."` (não passa por src/config.py)
- Validação de API key relaxada: aceita qualquer key não-vazia.
  LangSmith tem múltiplos formatos: ls__... (legado), lsv2_pt_... (Personal
  Token v2, atual), lsk_... (Service key). Validação real é responsabilidade
  da API do LangSmith no primeiro request.

ENV VARS NECESSÁRIAS:
    LANGCHAIN_TRACING_V2=true
    LANGCHAIN_API_KEY=<sua key, qualquer formato>
    LANGCHAIN_PROJECT=bluadiagnostics-sprint2   (opcional)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

# FIX V1.1: carregar .env no import deste módulo
# Isso garante que mesmo invocações standalone (`python -c "..."`) leiam o .env
try:
    from dotenv import load_dotenv
    # Procura .env subindo da raiz do projeto (parent.parent.parent = raiz)
    _project_root = Path(__file__).resolve().parent.parent.parent
    _env_path = _project_root / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    # python-dotenv não instalado — env vars devem vir do shell
    pass

logger = logging.getLogger(__name__)


@dataclass
class LangSmithStatus:
    """Status de configuração do LangSmith."""
    enabled: bool
    project: str
    has_api_key: bool
    api_key_preview: str = ""
    endpoint: str = "https://api.smith.langchain.com"
    motivo_desabilitado: str = ""


def get_langsmith_status() -> LangSmithStatus:
    """Verifica status do LangSmith via env vars."""
    tracing_on = os.getenv("LANGCHAIN_TRACING_V2", "").lower() in ("true", "1", "yes")
    api_key = os.getenv("LANGCHAIN_API_KEY", "").strip()
    project = os.getenv("LANGCHAIN_PROJECT", "default")
    endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

    # FIX V1.1: aceita qualquer key não-vazia (formatos atuais: ls__, lsv2_pt_, lsk_)
    has_key = bool(api_key)
    preview = ""
    if has_key:
        if len(api_key) >= 12:
            preview = f"{api_key[:8]}...{api_key[-4:]}"
        else:
            preview = "(key curta)"

    if not tracing_on:
        return LangSmithStatus(
            enabled=False,
            project=project,
            has_api_key=has_key,
            api_key_preview=preview,
            endpoint=endpoint,
            motivo_desabilitado="LANGCHAIN_TRACING_V2 não está 'true'",
        )

    if not has_key:
        return LangSmithStatus(
            enabled=False,
            project=project,
            has_api_key=False,
            endpoint=endpoint,
            motivo_desabilitado="LANGCHAIN_API_KEY ausente ou vazia",
        )

    return LangSmithStatus(
        enabled=True,
        project=project,
        has_api_key=True,
        api_key_preview=preview,
        endpoint=endpoint,
    )


def imprimir_status_startup() -> None:
    """Imprime status do LangSmith."""
    s = get_langsmith_status()
    if s.enabled:
        print(
            f"🔭 LangSmith ATIVO · projeto='{s.project}' · "
            f"key={s.api_key_preview}"
        )
        print(f"   Dashboard: https://smith.langchain.com/o/-/projects/p/{s.project}")
    else:
        print(f"⚪ LangSmith desativado: {s.motivo_desabilitado}")
        print("   Para ativar, adicione no .env:")
        print("     LANGCHAIN_TRACING_V2=true")
        print("     LANGCHAIN_API_KEY=<sua_key>")
        print("     LANGCHAIN_PROJECT=bluadiagnostics-sprint2")


def ensure_project(project_name: str | None = None) -> str:
    """Garante que LANGCHAIN_PROJECT está setado."""
    if project_name:
        os.environ["LANGCHAIN_PROJECT"] = project_name
    return os.environ.get("LANGCHAIN_PROJECT", "default")


def disable_langsmith() -> None:
    """Desativa LangSmith temporariamente."""
    os.environ["LANGCHAIN_TRACING_V2"] = "false"


def enable_langsmith() -> None:
    """Reativa LangSmith se a key estiver presente."""
    if os.getenv("LANGCHAIN_API_KEY"):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
