"""
Testes de regressão para prompts (BÔNUS Sprint 2).

Diferente de tests/test_tools.py (lógica determinística), aqui testamos
COMPORTAMENTO de prompts. Não são unit tests puros — chamam o LLM real.

Estratégia:
- Marcar como @pytest.mark.llm (skip por padrão, rodar com --run-llm)
- Cada caso: input + asserções soft (regex, contains, classifier)
- Snapshot testing: salvar outputs canônicos em tests/snapshots/
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 6-7
# Casos:
# - test_supervisor_classifica_triagem()
# - test_supervisor_classifica_red_flag_curto_circuita()
# - test_triagem_pergunta_sobre_sintoma_sem_diagnosticar()
# - test_prescricao_sempre_marca_requer_revisao_medica()
# - test_disclaimer_presente_em_resposta_clinica()
