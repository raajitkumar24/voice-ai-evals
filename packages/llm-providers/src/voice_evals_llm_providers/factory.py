from __future__ import annotations

from typing import Any

import httpx
from voice_evals_llm_gateway import LLMProvider, ProviderError, ProviderErrorCategory

from .anthropic import AnthropicProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider
from .openai import OpenAIProvider
from .openai_compatible import OpenAICompatibleProvider
from .test_provider import TestLLMProvider


def build_provider(
    provider: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    capability_overrides: dict[str, Any] | None = None,
    enable_test_provider: bool = False,
    client: httpx.AsyncClient | None = None,
) -> LLMProvider:
    if provider == "openai":
        if not api_key:
            raise _missing_key(provider)
        return OpenAIProvider(
            api_key, base_url=base_url or "https://api.openai.com/v1", client=client
        )
    if provider == "anthropic":
        if not api_key:
            raise _missing_key(provider)
        return AnthropicProvider(
            api_key, base_url=base_url or "https://api.anthropic.com/v1", client=client
        )
    if provider == "gemini":
        if not api_key:
            raise _missing_key(provider)
        return GeminiProvider(
            api_key,
            base_url=base_url or "https://generativelanguage.googleapis.com/v1beta",
            client=client,
        )
    if provider == "openai-compatible":
        if not base_url:
            raise ProviderError(
                provider,
                ProviderErrorCategory.INVALID_REQUEST,
                "OpenAI-compatible connections require a base URL",
            )
        overrides = {
            key: bool(value)
            for key, value in (capability_overrides or {}).items()
            if key
            in {
                "structured_output",
                "json_mode",
                "long_context",
                "multilingual",
                "tool_calling",
                "vision",
            }
        }
        return OpenAICompatibleProvider(
            base_url=base_url,
            api_key=api_key,
            capability_overrides=overrides,
            client=client,
        )
    if provider == "ollama":
        return OllamaProvider(base_url=base_url or "http://localhost:11434", client=client)
    if provider == "test" and enable_test_provider:
        return TestLLMProvider()
    raise ProviderError(
        provider,
        ProviderErrorCategory.INVALID_REQUEST,
        f"Unsupported provider '{provider}'",
    )


def _missing_key(provider: str) -> ProviderError:
    return ProviderError(
        provider,
        ProviderErrorCategory.AUTHENTICATION,
        f"{provider} requires a server-side API key",
    )
