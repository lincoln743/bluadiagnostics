"""
Observabilidade — logs estruturados + integração LangSmith (bônus).

DUAS camadas independentes:

1. Logs estruturados em JSONL (sempre ativo)
   - Cada agente acionado, cada tool chamada, cada retrieval do RAG
   - Arquivo: logs/trajectories.jsonl
   - Schema: {timestamp, conversation_id, agent, event_type, payload}
   - Suficiente para o critério de "logs estruturados de trajetória de agentes"

2. LangSmith (opcional via env var LANGSMITH_TRACING=true)
   - Traces visuais com timeline e árvore de chamadas
   - Ativado automaticamente se LANGSMITH_API_KEY estiver definida
   - Captura screenshots para o vídeo de demonstração

Implementação prevista (Dia 8-9):
- Classe TrajectoryLogger com método log_event(event_type, payload)
- Decorator @trace_agent para auto-instrumentar nós do grafo
- Setup LangSmith via env vars (auto-detecta)
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 8-9
