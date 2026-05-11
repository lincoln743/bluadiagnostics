"""
Tool: agendar_teleconsulta

Agenda teleconsulta em uma das 8 especialidades Care Plus.
Mock realista — gera ID de agendamento e horário disponível plausível.

Especialidades disponíveis (Care Plus telemedicina):
- clinica_medica
- cardiologia
- ginecologia
- pediatria
- dermatologia
- psiquiatria
- nutricao
- ortopedia

Urgências aceitas: rotina | prioridade | urgente

Implementação prevista (Dia 5):
- Função agendar_teleconsulta(paciente_id, especialidade, urgencia,
  motivo_resumido, janela_preferencial=None) -> dict
- Retorno: {agendamento_id, data_hora, profissional, link_video, instrucoes}
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 5
