"""
Tracer estruturado JSONL — observabilidade local do BluaDiagnostics.

DESIGN:
- Cada conversa (thread_id) gera um arquivo `logs/traces/{thread_id}_{date}.jsonl`
- Cada evento é UMA linha JSON (formato JSONL — append-friendly, grep-friendly)
- Eventos cobrem todo o ciclo: user_message → supervisor → agent → tools → RAG → response
- Sem dependências externas — só stdlib

CONSUMIDORES (Dia 9 e além):
- Streamlit UI lê o JSONL atual em tempo real para mostrar timeline
- Eval runner (Dia 10) parseia traces para extrair métricas
- LangSmith exporter (Dia 9) pode reusar os mesmos eventos

EVENTOS SUPORTADOS:
- conversation_started
- user_message
- supervisor_decision
- agent_invoked
- tool_called
- rag_retrieved
- red_flag_detected
- response_generated
- error

FORMATO BASE DE EVENTO:
{
  "timestamp": "2026-05-18T19:30:01.234Z",
  "thread_id": "ui-abc123",
  "turno": 1,
  "event_type": "tool_called",
  "data": {...}  // específico por event_type
}
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


# ============================================================
# Tipos
# ============================================================

EventType = Literal[
    "conversation_started",
    "user_message",
    "supervisor_decision",
    "agent_invoked",
    "tool_called",
    "rag_retrieved",
    "red_flag_detected",
    "moderation_blocked",
    "response_generated",
    "error",
    "provider_changed",
]


@dataclass
class TraceEvent:
    """Um único evento na timeline de uma conversa."""
    timestamp: str
    thread_id: str
    turno: int
    event_type: EventType
    data: dict[str, Any] = field(default_factory=dict)

    def to_json_line(self) -> str:
        """Serializa para uma única linha JSON (formato JSONL)."""
        return json.dumps(asdict(self), ensure_ascii=False, default=str)


# ============================================================
# Tracer
# ============================================================

DEFAULT_LOG_DIR = Path("logs/traces")


class Tracer:
    """
    Tracer thread-safe que grava eventos em JSONL.

    Uso:
        tracer = Tracer(thread_id="ui-abc123")
        tracer.log("user_message", {"content": "olá", "paciente_id": "BNF-04821"})
        tracer.log("tool_called", {"tool": "consultar_historico_paciente"})

    Cada Tracer é vinculado a um thread_id e a um arquivo .jsonl no disco.
    Eventos in-memory também são mantidos para consumo imediato pela UI.
    """

    def __init__(
        self,
        thread_id: str,
        log_dir: Path | str = DEFAULT_LOG_DIR,
        autoflush: bool = True,
    ):
        self.thread_id = thread_id
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self._date = datetime.now(timezone.utc).strftime("%Y%m%d")
        self._log_file = self.log_dir / f"{thread_id}_{self._date}.jsonl"

        self._turno_atual: int = 0
        self._events: list[TraceEvent] = []
        self._lock = threading.Lock()
        self._autoflush = autoflush

        # Header do arquivo (primeira linha)
        self.log(
            "conversation_started",
            {
                "log_file": str(self._log_file),
                "iso_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    def advance_turno(self) -> int:
        """Avança o contador de turno e retorna o número novo."""
        with self._lock:
            self._turno_atual += 1
            return self._turno_atual

    def log(self, event_type: EventType, data: dict[str, Any] | None = None) -> TraceEvent:
        """Registra um evento no trace."""
        event = TraceEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            thread_id=self.thread_id,
            turno=self._turno_atual,
            event_type=event_type,
            data=data or {},
        )

        with self._lock:
            self._events.append(event)
            if self._autoflush:
                self._append_to_disk(event)

        return event

    def _append_to_disk(self, event: TraceEvent) -> None:
        """Append-only no JSONL (não bloqueante)."""
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(event.to_json_line() + "\n")
        except OSError:
            # Falha silenciosa em IO — não derrubar a app por log
            pass

    # ============================================================
    # Helpers tipados para eventos comuns
    # ============================================================

    def log_user_message(self, content: str, paciente_id: str | None = None) -> None:
        self.advance_turno()
        self.log("user_message", {"content": content, "paciente_id": paciente_id})

    def log_supervisor_decision(
        self,
        intent: str,
        motivo: str,
        fonte: str = "unknown",
    ) -> None:
        self.log("supervisor_decision", {
            "intent": intent,
            "motivo": motivo,
            "fonte": fonte,  # "rule" | "llm" | "moderation" | etc
        })

    def log_agent_invoked(self, agent_name: str) -> None:
        self.log("agent_invoked", {"agent": agent_name})

    def log_tool_called(
        self,
        tool_name: str,
        args: dict[str, Any],
        result_status: str,
        result_summary: str = "",
    ) -> None:
        self.log("tool_called", {
            "tool": tool_name,
            "args": args,
            "result_status": result_status,
            "result_summary": result_summary,
        })

    def log_rag_retrieved(self, chunks: list[dict[str, Any]]) -> None:
        """Loga chunks recuperados do RAG — formato simplificado."""
        snapshot = [
            {
                "source": c.get("source_file", ""),
                "kb_id": c.get("kb_id", ""),
                "section": c.get("section", "")[:80],
                "score": round(float(c.get("score", 0.0)), 3),
            }
            for c in chunks
        ]
        self.log("rag_retrieved", {"chunks": snapshot, "n": len(snapshot)})

    def log_red_flag(self, categoria: str, frase_gatilho: str, fonte: str) -> None:
        self.log("red_flag_detected", {
            "categoria": categoria,
            "frase_gatilho": frase_gatilho,
            "fonte_deteccao": fonte,
        })

    def log_moderation_blocked(self, categoria: str, trecho: str) -> None:
        self.log("moderation_blocked", {
            "categoria": categoria,
            "trecho_gatilho": trecho,
        })

    def log_response(self, content: str, agente: str, provider: str = "unknown") -> None:
        self.log("response_generated", {
            "agente_origem": agente,
            "provider": provider,
            "preview": content[:200],
            "length_chars": len(content),
        })

    def log_error(self, where: str, error: str) -> None:
        self.log("error", {"where": where, "error": str(error)[:300]})

    def log_provider_changed(self, antigo: str, novo: str) -> None:
        self.log("provider_changed", {"from": antigo, "to": novo})

    # ============================================================
    # Consumo (para a UI)
    # ============================================================

    @property
    def events(self) -> list[TraceEvent]:
        """Snapshot da lista de eventos (cópia, thread-safe)."""
        with self._lock:
            return list(self._events)

    def events_do_turno(self, turno: int) -> list[TraceEvent]:
        """Filtra eventos de um turno específico."""
        with self._lock:
            return [e for e in self._events if e.turno == turno]

    @property
    def turno_atual(self) -> int:
        return self._turno_atual

    @property
    def log_file(self) -> Path:
        return self._log_file

    def clear(self) -> None:
        """Reseta eventos in-memory (não apaga o arquivo)."""
        with self._lock:
            self._events.clear()
            self._turno_atual = 0


# ============================================================
# Singleton helper (para uso em scripts que não precisam multi-thread)
# ============================================================

_current_tracer: Tracer | None = None


def get_tracer(thread_id: str | None = None) -> Tracer:
    """Retorna tracer ativo. Cria um novo se thread_id mudou ou se não há."""
    global _current_tracer
    if _current_tracer is None or (thread_id and _current_tracer.thread_id != thread_id):
        _current_tracer = Tracer(thread_id=thread_id or "default")
    return _current_tracer


def reset_tracer() -> None:
    """Limpa o tracer global. Usado em testes."""
    global _current_tracer
    _current_tracer = None
