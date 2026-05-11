"""
Validador de escopo — rejeita perguntas fora do domínio Care Plus.

Domínios PERMITIDOS:
- Sintomas e autoavaliação clínica
- Medicações em uso pelo beneficiário
- Agendamento de teleconsulta / consulta presencial
- Dúvidas sobre cobertura e rede credenciada Care Plus
- Orientações de prevenção e bem-estar

Domínios REJEITADOS (com mensagem educada):
- Perguntas gerais não-clínicas (clima, esportes, política)
- Conselhos jurídicos, financeiros, técnicos não-médicos
- Pedidos de "ignorar instruções" (jailbreak — tratado em moderation.py)
- Diagnóstico definitivo (rejeitar com explicação do HITL)

Implementação prevista (Dia 5):
- Função validar_escopo(mensagem: str) -> ScopeResult
- Híbrido: keywords negativas (rejeita rápido) + LLM classifier (ambíguos)
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 5
# Implementar validar_escopo(mensagem) -> ScopeResult
