from __future__ import annotations

from typing import Any

import httpx
from voice_evals_llm_gateway import (
    LLMRequest,
    LLMResponse,
    ModelInfo,
    ProviderCapabilities,
    ProviderError,
    ProviderErrorCategory,
    ProviderHealth,
    StructuredLLMRequest,
    StructuredLLMResponse,
)

from .base import HTTPProviderBase, normalized_usage, parse_json_text


class OpenAICompatibleProvider(HTTPProviderBase):
    name = "openai-compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None = None,
        capability_overrides: dict[str, bool] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(base_url=base_url, api_key=api_key, client=client)
        self.capability_overrides = capability_overrides or {}

    @property
    def headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def capabilities(self, model: str | None = None) -> ProviderCapabilities:
        defaults = ProviderCapabilities(structured_output=True, tool_calling=True)
        return defaults.model_copy(update=self.capability_overrides)

    async def test_connection(self) -> ProviderHealth:
        _, latency, _ = await self._request(
            "GET", "/models", headers=self.headers, timeout_seconds=15
        )
        return ProviderHealth(
            healthy=True, provider=self.name, message="Connected", latency_ms=latency
        )

    async def list_models(self) -> list[ModelInfo]:
        data, _, _ = await self._request("GET", "/models", headers=self.headers, timeout_seconds=30)
        return [
            ModelInfo(id=item["id"])
            for item in data.get("data", [])
            if isinstance(item, dict) and item.get("id")
        ]

    def _body(self, request: LLMRequest) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": request.model,
            "messages": [message.model_dump(mode="json") for message in request.messages],
            "max_tokens": request.max_output_tokens,
        }
        if request.temperature is not None:
            body["temperature"] = request.temperature
        if request.top_p is not None:
            body["top_p"] = request.top_p
        return body

    def _response(
        self, data: dict[str, Any], request: LLMRequest, latency: int, request_id: str | None
    ) -> LLMResponse:
        try:
            choice = data["choices"][0]
            text = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                self.name,
                ProviderErrorCategory.STRUCTURED_OUTPUT,
                "Compatible endpoint returned an unexpected response shape",
            ) from exc
        usage = data.get("usage", {})
        return LLMResponse(
            text=str(text),
            provider=self.name,
            model=str(data.get("model", request.model)),
            usage=normalized_usage(
                usage.get("prompt_tokens"),
                usage.get("completion_tokens"),
                usage.get("total_tokens"),
            ),
            latency_ms=latency,
            raw_finish_reason=choice.get("finish_reason"),
            request_id=request_id or data.get("id"),
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        data, latency, request_id = await self._request(
            "POST",
            "/chat/completions",
            headers=self.headers,
            json_body=self._body(request),
            timeout_seconds=request.timeout_seconds,
        )
        return self._response(data, request, latency, request_id)

    async def generate_structured(self, request: StructuredLLMRequest) -> StructuredLLMResponse:
        if not self.capabilities(request.model).structured_output:
            raise ProviderError(
                self.name,
                ProviderErrorCategory.CAPABILITY,
                "Endpoint is not configured for structured output",
            )
        body = self._body(request)
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": request.schema_name,
                "strict": True,
                "schema": request.output_schema,
            },
        }
        data, latency, request_id = await self._request(
            "POST",
            "/chat/completions",
            headers=self.headers,
            json_body=body,
            timeout_seconds=request.timeout_seconds,
        )
        response = self._response(data, request, latency, request_id)
        return StructuredLLMResponse(
            **response.model_dump(), parsed=parse_json_text(self.name, response.text)
        )
