"""
LLM Provider — abstração para Groq (cloud) e Ollama (local).

V1.2 — Dia 6: adicionado OllamaProvider para BÔNUS LGPD.

JUSTIFICATIVA LGPD:
A Lei Geral de Proteção de Dados (Art. 5º, II) classifica dados de saúde como
"dados pessoais sensíveis". O Ollama permite rodar o LLM 100% on-premise — os
dados clínicos do beneficiário nunca saem do dispositivo. Isso é especialmente
relevante para o contexto Care Plus, onde:
- Histórico médico não pode ser enviado para servidores externos sem
  consentimento explícito do titular (Art. 11)
- Operadoras de saúde têm obrigação de minimização de dados (Art. 6º, III)
- Para implantações em ambiente hospitalar com Wi-Fi controlado, modelo local
  é a única arquitetura compatível com a regulação

TRADE-OFF DE ENGENHARIA:
- Groq Llama 3.1 8B: ~200 tok/s, latência <2s, sem custo no tier free
- Ollama Llama 3.2 3B em CPU (ThinkPad T430u): 3-8 tok/s, latência 15-45s
- Recomendado em produção: Groq como default + Ollama opcional via
  configuração do tenant Care Plus para clientes corporate com exigências LGPD.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from groq import APIStatusError, Groq, RateLimitError
from openai import OpenAI
from openai import APIStatusError as OpenAIAPIError
from openai import APITimeoutError, APIConnectionError
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
    provider_name: str = "unknown"  # NOVO V1.2 — para tracing


def _anthropic_to_openai_tool(tool_spec: dict[str, Any]) -> dict[str, Any]:
    """Converte spec de tool do formato Anthropic para OpenAI/Groq/Ollama."""
    return {
        "type": "function",
        "function": {
            "name": tool_spec["name"],
            "description": tool_spec["description"],
            "parameters": tool_spec["input_schema"],
        },
    }


# ============================================================
# Groq Provider (v1.1 — sem mudanças no Dia 6)
# ============================================================

class GroqProvider:
    """Provider Groq via SDK oficial com retry em rate limit."""

    name = "groq"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model_principal
        if not self.api_key:
            raise ValueError("GROQ_API_KEY não configurada — confira .env")
        self.client = Groq(api_key=self.api_key)

    @retry(
        retry=retry_if_exception_type((RateLimitError,)),
        wait=wait_exponential(multiplier=5, min=5, max=40),
        stop=stop_after_attempt(4),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _call_with_retry(self, **params) -> Any:
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
            logger.error(f"Rate limit Groq persistente após 4 tentativas: {exc}")
            return LLMResponse(
                text="Sistema enfrentando alta demanda. Tente novamente em instantes.",
                tool_calls=[],
                finish_reason="rate_limit_exhausted",
                usage={"input_tokens": 0, "output_tokens": 0, "total": 0},
                raw=None,
                provider_name="groq",
            )
        except APIStatusError as exc:
            logger.error(f"Erro API Groq: status={exc.status_code}")
            raise

        choice = response.choices[0]
        msg = choice.message

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
            provider_name="groq",
        )


# ============================================================
# Ollama Provider (V1.2 — NOVO, BÔNUS LGPD)
# ============================================================

class OllamaProvider:
    """
    Provider Ollama via SDK openai compatível.

    Ollama expõe /v1/chat/completions no formato OpenAI a partir da v0.1.14.
    Aqui usamos o SDK openai apontando para localhost:11434/v1 — zero código
    duplicado do GroqProvider para parsing de response.

    Retry em timeouts/connection errors (modelo pode demorar minutos em CPU).
    """

    name = "ollama"

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/") + "/v1"
        self.model = model or settings.ollama_model
        # api_key obrigatória pelo SDK mas Ollama ignora o valor — usamos placeholder
        self.client = OpenAI(base_url=self.base_url, api_key="ollama-no-key-needed")

    @retry(
        retry=retry_if_exception_type((APITimeoutError, APIConnectionError)),
        wait=wait_exponential(multiplier=5, min=5, max=30),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _call_with_retry(self, **params) -> Any:
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
        params: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else settings.temperature,
            "max_tokens": max_tokens if max_tokens is not None else settings.max_tokens,
            "top_p": top_p if top_p is not None else settings.top_p,
            # Timeout generoso — modelos rodando em CPU podem ser lentos
            "timeout": 180.0,
        }

        if tools:
            params["tools"] = [_anthropic_to_openai_tool(t) for t in tools]
            # Ollama suporta tool_choice mas com qualidade variável em modelos pequenos
            params["tool_choice"] = "auto"

        try:
            response = self._call_with_retry(**params)
        except (APITimeoutError, APIConnectionError) as exc:
            logger.error(f"Ollama timeout/conexão após retries: {exc}")
            return LLMResponse(
                text=(
                    "O modelo local está sobrecarregado neste momento. "
                    "Para garantir uma resposta rápida, considere usar o "
                    "provider Groq ou agendar uma teleconsulta."
                ),
                tool_calls=[],
                finish_reason="ollama_timeout",
                usage={"input_tokens": 0, "output_tokens": 0, "total": 0},
                raw=None,
                provider_name="ollama",
            )
        except OpenAIAPIError as exc:
            logger.error(f"Erro Ollama API: status={getattr(exc, 'status_code', '?')}")
            raise

        choice = response.choices[0]
        msg = choice.message

        tool_calls: list[dict[str, Any]] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                })

        # Ollama nem sempre retorna usage — proteção
        usage = {
            "input_tokens": getattr(response.usage, "prompt_tokens", 0) if response.usage else 0,
            "output_tokens": getattr(response.usage, "completion_tokens", 0) if response.usage else 0,
            "total": getattr(response.usage, "total_tokens", 0) if response.usage else 0,
        }

        return LLMResponse(
            text=msg.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage,
            raw=response,
            provider_name="ollama",
        )


# ============================================================
# Factory (V1.2 atualizado — agora suporta Ollama)
# ============================================================

# Singleton por provider name
_provider_instances: dict[str, GroqProvider | OllamaProvider] = {}


def get_provider(force_provider: str | None = None) -> GroqProvider | OllamaProvider:
    """
    Retorna a instância do provider ativo.

    Args:
        force_provider: opcional, força um provider específico ("groq"|"ollama")
                        ignorando settings.llm_provider. Útil para smoke tests
                        que querem comparar os dois sem mexer no .env.
    """
    provider_name = force_provider or settings.llm_provider

    if provider_name in _provider_instances:
        return _provider_instances[provider_name]

    if provider_name == "groq":
        instance = GroqProvider()
    elif provider_name == "ollama":
        instance = OllamaProvider()
    else:
        raise ValueError(f"LLM_PROVIDER inválido: {provider_name} (use 'groq' ou 'ollama')")

    _provider_instances[provider_name] = instance
    return instance


def reset_provider_cache() -> None:
    """Limpa cache de singletons. Útil em testes."""
    global _provider_instances
    _provider_instances = {}
