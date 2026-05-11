"""
Interface Streamlit do BluaDiagnostics.

Layout do briefing:
- Chat central com histórico da conversa
- Painel lateral mostrando:
  * Trajetória dos agentes acionados (visual: badges coloridos)
  * Documentos recuperados pelo RAG no último turno (com source + score)
  * Tools chamadas (com args e result colapsáveis)
  * Métricas: tempo de resposta, tokens consumidos

Esse painel lateral é CRÍTICO para o vídeo de demonstração — torna o RAG
e o roteamento visíveis (exigências explícitas do briefing).

Implementação prevista (Dia 8-9):
- st.chat_input + st.chat_message para conversa
- st.sidebar com expanders para cada categoria de info
- Botão "Reset conversa" para demo
- Seletor de paciente (BNF-04821 Maria por padrão)
- Toggle "Mostrar trajetória detalhada" (default ON para demo)
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 8-9
