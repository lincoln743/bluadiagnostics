"""
Agente de Triagem — conduz o Digital Check-up.

Responsabilidades:
- Coletar sintomas de forma estruturada e acolhedora
- Consultar histórico do paciente (tool: consultar_historico_paciente)
- Recuperar contexto clínico via RAG (tool: buscar_conhecimento_clinico)
- Aplicar protocolo Manchester (kb01) para classificação de urgência
- NUNCA diagnosticar — sempre encaminhar para validação médica
- Sugerir teleconsulta quando apropriado (tool: agendar_teleconsulta)

Tools habilitadas neste agente:
- consultar_historico_paciente
- buscar_conhecimento_clinico
- consultar_wearables (bônus)
- agendar_teleconsulta

Implementação prevista (Dia 3-4):
- Função triagem_node(state) -> dict
- System prompt: prompts/system_prompts.py::TRIAGEM_PROMPT
- Few-shot: prompts/few_shots.py::TRIAGEM_EXAMPLES
- Modelo: 70B nos turnos críticos (decisão de escalada), 8B nos turnos
  conversacionais (coleta de sintomas)
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 3-4
# Implementar triagem_node(state: BluaState) -> dict
