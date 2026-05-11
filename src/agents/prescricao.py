"""
Agente de Prescrição — sugere prescrições para validação MÉDICA (HITL).

PRINCÍPIO INEGOCIÁVEL: este agente NUNCA emite prescrição final.
Ele SUGERE um esboço que é enviado para um médico validar.

Responsabilidades:
- Consultar histórico do paciente para identificar contraindicações
- Verificar interações medicamentosas (tool: verificar_interacoes_medicamentosas)
- Consultar bulas resumidas via RAG (kb02_bulas_resumidas.md)
- Gerar sugestão estruturada em formato JSON: medicamento, dose, frequência,
  duração, justificativa, alertas, requer_revisao_medica=True (SEMPRE)
- Interromper o grafo aqui (LangGraph interrupt) para HITL

Tools habilitadas:
- consultar_historico_paciente
- verificar_interacoes_medicamentosas
- buscar_conhecimento_clinico

Implementação prevista (Dia 4):
- Função prescricao_node(state) -> dict
- Estrutura de saída: pydantic.PrescricaoSugerida
- Modelo: SEMPRE 70B aqui (precisão > custo)
- interrupt_before=["prescricao"] no graph builder
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 4
# Implementar prescricao_node(state: BluaState) -> dict
# Reusar paciente mock da Sprint 1 (BNF-04821 = Maria, hipertensa, Losartana 50mg)
