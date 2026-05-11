"""
Tool: consultar_wearables — BÔNUS Sprint 2 (wearables mockados)

Retorna dados simulados de wearables (Apple Health, Google Fit, Oura)
para enriquecer o check-up digital.

Dados mockados:
- Frequência cardíaca: repouso, média do dia, máxima
- Pressão arterial estimada (Apple Watch Series 9+)
- Saturação de O2 (SpO2)
- Sono: total, qualidade, REM, despertar noturno
- Passos: meta e realizado
- HRV (variabilidade): indicador de estresse
- Eventos anormais detectados: arritmia, queda

Uso pelo agente de triagem:
- Maria reclama de "cansaço" -> consulta wearable -> vê HRV baixo + sono ruim
- Correlaciona com hipertensão e Losartana
- Sugere ajuste de horário da medicação + teleconsulta com cardio

Implementação prevista (Dia 5-6):
- Função consultar_wearables(paciente_id, periodo_dias=7) -> dict
- Dados estáticos em data/mock_wearables.json
- Padronizar formato Apple HealthKit (objeto de referência da indústria)
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 5-6 (BÔNUS)
