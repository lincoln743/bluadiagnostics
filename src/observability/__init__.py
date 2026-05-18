"""Observabilidade local — tracer JSONL para o BluaDiagnostics."""
from src.observability.tracer import (
    Tracer,
    TraceEvent,
    get_tracer,
    reset_tracer,
)

__all__ = ["Tracer", "TraceEvent", "get_tracer", "reset_tracer"]
