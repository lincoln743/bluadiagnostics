"""
Moderação de conteúdo — bloqueia jailbreaks e prompt injections.

Padrões detectados:
- "ignore previous instructions" / "esqueça suas instruções"
- "you are now [persona alternativa]"
- "DAN mode", "developer mode", "jailbreak"
- Pedidos de revelar system prompt
- Pedidos de prescrever sem revisão médica

Implementação prevista (Dia 5):
- Função moderar(mensagem: str) -> ModerationResult{bloqueado, motivo, severidade}
- Heurística rule-based + classificador LLM para casos sofisticados
- Logging de TODO bloqueio (para o eval set e relatório)
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 5
# Implementar moderar() — reusar casos de jailbreak do sprint1_eval_set.json
