"""
Agente Supervisor — roteador central do sistema multi-agente.

Responsabilidades:
- Ler a última mensagem do usuário
- Classificar a intent (triagem / prescricao / escalada / fora_de_escopo)
- Detectar red flags ANTES de qualquer outra coisa (guardrail prioritário)
- Atualizar state["intent"] e state["proximo_agente"]
- NÃO conversa diretamente com o usuário (não gera resposta final)

Implementação prevista (Dia 3):
- Função supervisor_node(state) -> dict
- Usa LLM (modelo 8B é suficiente — tarefa de classificação simples)
- Few-shot com 6 exemplos no prompt (2 triagem, 2 prescricao, 1 escalada, 1 fora_de_escopo)
- Antes de classificar: roda guardrails.red_flags.detectar() na mensagem
  Se True -> intent = "escalada" (curto-circuito)
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 3
# Implementar supervisor_node(state: BluaState) -> dict
