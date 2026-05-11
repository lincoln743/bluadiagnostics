"""
Agente de Escalada Humana — ativado quando red flag é detectada.

Responsabilidades:
- Gerar mensagem de orientação clara e CALMA (não amplificar pânico)
- Orientar SAMU 192 (emergências clínicas) ou CVV 188 (crise psicológica)
- Registrar evento de escalada para auditoria
- Finalizar a conversa (state["conversa_finalizada"] = True)

Princípio de tom:
- Direto mas acolhedor
- Sem floreios
- Instrução acionável imediata
- NUNCA diagnosticar a condição

Exemplo de output:
    "Maria, pelo que você descreveu, é importante buscar atendimento médico
    AGORA. Por favor, ligue para o SAMU 192 ou vá ao pronto-socorro mais
    próximo. Se estiver acompanhada, peça ajuda. Estou aqui se precisar."

Implementação prevista (Dia 5):
- Função escalada_node(state) -> dict
- Template de resposta parametrizado por tipo de red flag
- Logging crítico do evento (observability)
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 5
# Implementar escalada_node(state: BluaState) -> dict
