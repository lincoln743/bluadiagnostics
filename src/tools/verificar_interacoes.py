"""
Tool: verificar_interacoes_medicamentosas

Verifica interações entre medicamentos. Reusa a base mock da Sprint 1
(4 pares de interações conhecidas) e expande para cobrir Losartana
(medicação contínua da Maria).

Interações cobertas (mock):
- Losartana + AINEs (ibuprofeno, diclofenaco): redução do efeito anti-HTA
- Atorvastatina + claritromicina: risco de rabdomiólise
- Varfarina + AAS: risco aumentado de sangramento
- Sertralina + tramadol: síndrome serotoninérgica
- Dipirona + paciente alérgico: contraindicação absoluta

Implementação prevista (Dia 5):
- Função verificar_interacoes_medicamentosas(medicamentos, paciente_id=None,
  aprovado_por_medico=False) -> dict
- Importante: parâmetro aprovado_por_medico exigido para retornar prescrição
  (reforço do HITL no nível da tool)
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 5
