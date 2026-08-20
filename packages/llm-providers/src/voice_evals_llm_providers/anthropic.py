from __future__ import annotations

from typing import Any

import httpx
from voice_evals_llm_gateway import (
    LLMRequest,
    LLMResponse,
    MessageRole,
    ModelInfo,
    ProviderCapabilities,
    ProviderError,
    ProviderErrorCategory,
    ProviderHealth,
    StructuredLLMRequest,
    StructuredLLMResponse,
)

from .base import HTTPProviderBase, normalized_usage, parse_json_text


class AnthropicProvider(HTTPProviderBase):
    name = "anthropic"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.anthropic.com/v1",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(base_url=base_url, api_key=api_key, client=client)

    @property
    def headers(self) -> dict[str, str]:
        return {
            "x-api-key": str(self.api_key),
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    def capabilities(self, model: str | None = None) -> ProviderCapabilities:
        return ProviderCapabilities(structured_output=True, tool_calling=True, vision=True)

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
            ModelInfo(id=item["id"], display_name=item.get("display_name"))
            for item in data.get("data", [])
            if isinstance(item, dict) and item.get("id")
        ]

    def _body(self, request: LLMRequest) -> dict[str, Any]:
        system_parts: list[str] = []
        messages: list[dict[str, str]] = []
        for message in request.messages:
            if message.role in {MessageRole.SYSTEM, MessageRole.DEVELOPER}:
                system_parts.append(message.content)
            else:
                role = "assistant" if message.role == MessageRole.ASSISTANT else "user"
                messages.append({"role": role, "content": message.content})
        body: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_output_tokens,
            "messages": messages,
        }
        if system_parts:
            body["system"] = "\n\n".join(system_parts)
        if request.temperature is not None:
            body["temperature"] = request.temperature
        if request.top_p is not None:
            body["top_p"] = request.top_p
        return body

    @staticmethod
    def _text(data: dict[str, Any]) -> str:
        for block in data.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                return str(block.get("text", ""))
        raise ProviderError(
            "anthropic",
            ProviderErrorCategory.STRUCTURED_OUTPUT,
            "Anthropic response did not contain a text block",
        )

    def _response(
        self, data: dict[str, Any], request: LLMRequest, latency: int, request_id: str | None
    ) -> LLMResponse:
        usage = data.get("usage", {})
        return LLMResponse(
            text=self._text(data),
            provider=self.name,
            model=str(data.get("model", request.model)),
            usage=normalized_usage(usage.get("input_tokens"), usage.get("output_tokens")),
            latency_ms=latency,
            raw_finish_reason=data.get("stop_reason"),
            request_id=request_id or data.get("id"),
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        data, latency, request_id = await self._request(
            "POST",
            "/messages",
            headers=self.headers,
            json_body=self._body(request),
            timeout_seconds=request.timeout_seconds,
        )
        return self._response(data, request, latency, request_id)

    async def generate_structured(self, request: StructuredLLMRequest) -> StructuredLLMResponse:
        body = self._body(request)
        body["output_config"] = {"format": {"type": "json_schema", "schema": request.output_schema}}
        data, latency, request_id = await self._request(
            "POST",
            "/messages",
            headers=self.headers,
            json_body=body,
            timeout_seconds=request.timeout_seconds,
        )
        response = self._response(data, request, latency, request_id)
        return StructuredLLMResponse(
            **response.model_dump(), parsed=parse_json_text(self.name, response.text)
        )
