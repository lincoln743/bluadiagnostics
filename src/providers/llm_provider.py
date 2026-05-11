"""
Abstração de LLM Provider — Groq (cloud) ou Ollama (local).

Permite trocar o provider via env var LLM_PROVIDER sem alterar o resto do código.
Justificativa LGPD: Ollama mantém dados de saúde 100% on-premise — alinhamento
direto com o Art. 5º, II da LGPD (dados de saúde como dados pessoais sensíveis).

Implementação prevista (Dia 6-7):
- Classe abstrata LLMProvider com método chat_completion(messages, tools)
- GroqProvider usa o SDK groq
- OllamaProvider usa o SDK openai com base_url customizado (Ollama é compatível
  com o protocolo OpenAI Chat Completions desde a v0.1.14)
- Factory get_provider() retorna a instância correta baseada em settings.llm_provider
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 6-7
# Implementar:
# 1. ABC LLMProvider com método unificado chat_completion()
# 2. GroqProvider (refatorar do notebook da Sprint 1)
# 3. OllamaProvider (cliente OpenAI-compat apontando para localhost:11434)
# 4. Factory get_provider() lendo settings.llm_provider
# 5. Conversão automática tools_spec.json (formato Anthropic) -> formato OpenAI/Groq
#    Reusar a função do notebook da Sprint 1.
