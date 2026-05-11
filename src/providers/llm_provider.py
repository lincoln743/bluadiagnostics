"""
LLM Provider — abstração para chamar Groq (e futuramente Ollama).

Por que abstração?
- Hoje (Dia 3): usamos Groq via SDK groq (cloud).
- Dia 6: vamos plugar Ollama (local) como provider alternativo via env var.
- Sem essa abstração, teríamos `groq.Groq()` espalhado por 4-6 arquivos
  e a troca para Ollama exigiria edits massivos.

Princípio: cada agente chama `chat_completion(messages, tools=None)` sem se
importar com o provider concreto.

Conversão automática de tools:
- tools_spec em formato Anthropic → formato OpenAI/Groq.
- Mantém compatibilidade com tools que escrevermos pensando em Anthropic
  (formato mais limpo).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from groq import Groq

from src.config import settings


@dataclass
class LLMResponse:
    """Resposta normalizada do LLM (independe do provider)."""
    text: str                            # texto da resposta (vazio se chamou tool)
    tool_calls: list[dict[str, Any]]     # lista de chamadas de tool, se houver
    finish_reason: str                   # "stop" | "tool_calls" | "length" | "error"
    usage: dict[str, int]                # {input_tokens, output_tokens, total}
    raw: Any = None                      # objeto bruto do SDK (debugging)


def _anthropic_to_openai_tool(tool_spec: dict[str, Any]) -> dict[str, Any]:
    """
    Converte spec de tool do formato Anthropic para formato OpenAI/Groq.

    Anthropic:
        {"name": "...", "description": "...", "input_schema": {...}}
    OpenAI/Groq:
        {"type": "function", "function": {"name", "description", "parameters"}}
    """
    return {
        "type": "function",
        "function": {
            "name": tool_spec["name"],
            "description": tool_spec["description"],
            "parameters": tool_spec["input_schema"],
        },
    }


class GroqProvider:
    """Provider Groq via SDK oficial."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model_principal
        if not self.api_key:
            raise ValueError("GROQ_API_KEY não configurada — confira .env")
        self.client = Groq(api_key=self.api_key)

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """
        Chama o modelo via Chat Completions API (compatível com OpenAI).

        Args:
            messages: histórico no formato OpenAI [{"role", "content"}, ...]
            tools: specs de tools em formato Anthropic (serão convertidas)
            temperature, max_tokens, top_p: overrides; default vem do settings
            model: override do modelo (útil para subir para 70B em casos críticos)
        """
        # Defaults vêm da config
        params: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else settings.temperature,
            "max_tokens": max_tokens if max_tokens is not None else settings.max_tokens,
            "top_p": top_p if top_p is not None else settings.top_p,
        }

        if tools:
            params["tools"] = [_anthropic_to_openai_tool(t) for t in tools]
            params["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**params)
        choice = response.choices[0]
        msg = choice.message

        # Normaliza tool_calls (Groq retorna objetos, queremos dicts)
        tool_calls: list[dict[str, Any]] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,  # string JSON
                })

        usage = {
            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
            "output_tokens": response.usage.completion_tokens if response.usage else 0,
            "total": response.usage.total_tokens if response.usage else 0,
        }

        return LLMResponse(
            text=msg.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage,
            raw=response,
        )


# Singleton — instanciado lazy quando o primeiro agente chamar
_provider_instance: GroqProvider | None = None


def get_provider() -> GroqProvider:
    """
    Retorna a instância do provider ativo (singleton).

    Dia 6: vai virar factory que olha settings.llm_provider e retorna
    GroqProvider OU OllamaProvider conforme env var.
    """
    global _provider_instance
    if _provider_instance is None:
        if settings.llm_provider == "groq":
            _provider_instance = GroqProvider()
        elif settings.llm_provider == "ollama":
            raise NotImplementedError(
                "OllamaProvider será implementado no Dia 6 da Sprint 2"
            )
        else:
            raise ValueError(f"LLM_PROVIDER inválido: {settings.llm_provider}")
    return _provider_instance
