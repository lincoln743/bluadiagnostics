"""
LLM Provider — abstração para chamar Groq (e futuramente Ollama).

V1.1 — Dia 4b: adicionado retry com backoff exponencial para lidar com
rate limit do tier free Groq (6000 tokens/min). Usa `tenacity` (já estava
nas dependências do projeto).

Quando o Groq retorna 429 (rate limit), tentamos novamente com espera
crescente: 5s → 10s → 20s → 40s (até 4 tentativas, max ~75s).
Para erros não-recuperáveis (401, 400 etc), falha imediatamente.

Mantém retro-compatibilidade total: API pública de `GroqProvider.chat_completion`
não mudou — só ganhou resiliência interna.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from groq import APIStatusError, Groq, RateLimitError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Resposta normalizada do LLM (independe do provider)."""
    text: str
    tool_calls: list[dict[str, Any]]
    finish_reason: str
    usage: dict[str, int]
    raw: Any = None


def _anthropic_to_openai_tool(tool_spec: dict[str, Any]) -> dict[str, Any]:
    """Converte spec de tool do formato Anthropic para formato OpenAI/Groq."""
    return {
        "type": "function",
        "function": {
            "name": tool_spec["name"],
            "description": tool_spec["description"],
            "parameters": tool_spec["input_schema"],
        },
    }


class GroqProvider:
    """Provider Groq com retry automático em rate limit."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model_principal
        if not self.api_key:
            raise ValueError("GROQ_API_KEY não configurada — confira .env")
        self.client = Groq(api_key=self.api_key)

    # ============================================================
    # Chamada interna ao SDK com retry — V1.1
    # ============================================================
    # Retry condições:
    # - RateLimitError (429) → backoff 5s, 10s, 20s, 40s (max 4 tentativas)
    # - Outros APIStatusError (5xx) → mesmo padrão
    # - Erros 4xx (exceto 429) → falha imediata (não tem o que reentregar)
    #
    # Usar @retry como método decorado em classe é tricky — usamos closure
    # via método separado para preservar `self`.
    @retry(
        retry=retry_if_exception_type((RateLimitError,)),
        wait=wait_exponential(multiplier=5, min=5, max=40),  # 5, 10, 20, 40
        stop=stop_after_attempt(4),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _call_with_retry(self, **params) -> Any:
        """Chamada bruta ao SDK Groq com retry em rate limit."""
        return self.client.chat.completions.create(**params)

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """Chama o modelo via Chat Completions API. Com retry automático em 429."""
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

        try:
            response = self._call_with_retry(**params)
        except RateLimitError as exc:
            # Esgotou retries — fallback gracioso
            logger.error(f"Rate limit Groq persistente após 4 tentativas: {exc}")
            return LLMResponse(
                text=(
                    "Estou enfrentando alta demanda no momento. "
                    "Por favor, tente novamente em alguns instantes ou agende "
                    "uma teleconsulta pelo app Blua."
                ),
                tool_calls=[],
                finish_reason="rate_limit_exhausted",
                usage={"input_tokens": 0, "output_tokens": 0, "total": 0},
                raw=None,
            )
        except APIStatusError as exc:
            # Erros 4xx (não 429) ou 5xx persistentes
            logger.error(f"Erro API Groq: status={exc.status_code} body={exc.body}")
            raise

        choice = response.choices[0]
        msg = choice.message

        # Normaliza tool_calls
        tool_calls: list[dict[str, Any]] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
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


# Singleton — instanciado lazy
_provider_instance: GroqProvider | None = None


def get_provider() -> GroqProvider:
    """Retorna a instância do provider ativo (singleton)."""
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
