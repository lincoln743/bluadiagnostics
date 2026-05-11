"""
Tool: consultar_historico_paciente

Retorna histórico clínico simulado do beneficiário. Reusa o mock da Sprint 1
com adição do paciente canônico Maria (briefing Sprint 2).

Pacientes mock disponíveis:
- BNF-04821: "Maria", 34 anos, hipertensa, Losartana 50mg, última consulta
  03/2026 com Dr. João (paciente canônico do briefing Sprint 2)
- BNF-09732: "João", 58 anos, diabético tipo 2, Metformina
- BNF-15604: "Ana", 28 anos, sem comorbidades, gestante 22 semanas

Implementação prevista (Dia 5):
- Função consultar_historico_paciente(paciente_id, campos=None) -> dict
- Validação: paciente_id deve seguir padrão BNF-XXXXX
- Retorno estruturado: idade, sexo, condições, alergias, medicamentos,
  últimas consultas, exames recentes
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 5
# Implementar tool com paciente canônico Maria + os 2 da Sprint 1
