from __future__ import annotations

import json
import time
from typing import Any

import httpx
from voice_evals_llm_gateway import (
    NormalizedUsage,
    ProviderError,
    ProviderErrorCategory,
)


class HTTPProviderBase:
    name: str

    def __init__(self, *, base_url: str, api_key: str | None, client: httpx.AsyncClient | None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = client or httpx.AsyncClient()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        timeout_seconds: float = 60,
    ) -> tuple[dict[str, Any], int, str | None]:
        started = time.monotonic()
        try:
            response = await self.client.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                json=json_body,
                timeout=timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise ProviderError(
                self.name,
                ProviderErrorCategory.TIMEOUT,
                f"{self.name} request timed out",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderError(
                self.name,
                ProviderErrorCategory.TRANSIENT,
                f"{self.name} connection failed",
                retryable=True,
            ) from exc
        latency_ms = int((time.monotonic() - started) * 1000)
        if response.status_code >= 400:
            self._raise_status(response.status_code)
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise ProviderError(
                self.name,
                ProviderErrorCategory.STRUCTURED_OUTPUT,
                f"{self.name} returned a non-JSON API response",
                retryable=response.status_code >= 500,
                status_code=response.status_code,
            ) from exc
        if not isinstance(data, dict):
            raise ProviderError(
                self.name,
                ProviderErrorCategory.STRUCTURED_OUTPUT,
                f"{self.name} returned an unexpected API response shape",
            )
        return data, latency_ms, response.headers.get("x-request-id")

    def _raise_status(self, status_code: int) -> None:
        if status_code in {401, 403}:
            category = ProviderErrorCategory.AUTHENTICATION
            retryable = False
        elif status_code == 429:
            category = ProviderErrorCategory.RATE_LIMIT
            retryable = True
        elif status_code >= 500:
            category = ProviderErrorCategory.TRANSIENT
            retryable = True
        else:
            category = ProviderErrorCategory.INVALID_REQUEST
            retryable = False
        # Upstream bodies are omitted because they can echo credentials or transcript data.
        raise ProviderError(
            self.name,
            category,
            f"{self.name} request failed with HTTP {status_code}",
            retryable=retryable,
            status_code=status_code,
        )


def parse_json_text(provider: str, text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError(
            provider,
            ProviderErrorCategory.STRUCTURED_OUTPUT,
            f"{provider} returned malformed structured output",
            retryable=True,
        ) from exc
    if not isinstance(parsed, dict):
        raise ProviderError(
            provider,
            ProviderErrorCategory.STRUCTURED_OUTPUT,
            f"{provider} structured output must be a JSON object",
            retryable=True,
        )
    return parsed


def normalized_usage(
    input_tokens: Any, output_tokens: Any, total_tokens: Any = None
) -> NormalizedUsage:
    input_count = int(input_tokens or 0)
    output_count = int(output_tokens or 0)
    return NormalizedUsage(
        input_tokens=input_count,
        output_tokens=output_count,
        total_tokens=int(total_tokens or input_count + output_count),
    )
