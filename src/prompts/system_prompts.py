"""
System prompts versionados como código (não como string hardcoded espalhada).

Permite:
- Diff legível entre versões
- Testes unitários nos prompts
- Reuso entre agentes (compor blocos)

Estrutura: cada prompt é uma constante UPPERCASE com docstring explicando
seu propósito. Versionamento via tag no docstring (ex: # v1.0, # v1.1).

Implementação prevista (Dia 3-4 + iteração contínua até Dia 10):
- SUPERVISOR_PROMPT (classificação de intent)
- TRIAGEM_PROMPT (check-up digital, tom acolhedor)
- PRESCRICAO_PROMPT (rigor clínico, HITL obrigatório)
- ESCALADA_PROMPT (orientação calma para emergência)
- DISCLAIMER_PADRAO (rodapé legal em respostas clínicas)
- Blocos compartilhados: PERSONA_BLOCK, RED_FLAG_BLOCK, REFUSAL_BLOCK

Documentação de iterações:
- Cada mudança que melhore o eval score deve ser registrada no
  README.md seção "Iterações de Prompt" (critério explícito do briefing)
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 3 (versão inicial) + iterações até Dia 10
# Reusar prompts/system_prompt.md da Sprint 1 como base
