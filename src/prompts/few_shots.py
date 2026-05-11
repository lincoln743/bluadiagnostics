"""
Exemplos few-shot por agente.

Few-shot prompting é um dos diferenciais reconhecidos no briefing
(seção "Técnicas avançadas de prompting" — bônus).

Estrutura: lista de tuplas (input, output_esperado) por agente.
Output em JSON quando o agente tem structured output (supervisor, prescricao).

Implementação prevista (Dia 4 + iteração):
- SUPERVISOR_EXAMPLES: 6 exemplos cobrindo as 4 intents
- TRIAGEM_EXAMPLES: 4 exemplos de check-up bem-conduzido
- PRESCRICAO_EXAMPLES: 3 exemplos de sugestão estruturada
- Função format_few_shots(examples, style="chatml") -> str
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 4
