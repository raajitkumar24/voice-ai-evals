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


class OllamaProvider(HTTPProviderBase):
    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(base_url=base_url, api_key=None, client=client)

    def capabilities(self, model: str | None = None) -> ProviderCapabilities:
        return ProviderCapabilities(structured_output=True, tool_calling=True)

    async def test_connection(self) -> ProviderHealth:
        _, latency, _ = await self._request("GET", "/api/tags", timeout_seconds=15)
        return ProviderHealth(
            healthy=True, provider=self.name, message="Connected", latency_ms=latency
        )

    async def list_models(self) -> list[ModelInfo]:
        data, _, _ = await self._request("GET", "/api/tags", timeout_seconds=30)
        return [
            ModelInfo(id=item["name"], display_name=item.get("model"))
            for item in data.get("models", [])
            if isinstance(item, dict) and item.get("name")
        ]

    def _body(self, request: LLMRequest) -> dict[str, Any]:
        options: dict[str, Any] = {"num_predict": request.max_output_tokens}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.top_p is not None:
            options["top_p"] = request.top_p
        return {
            "model": request.model,
            "messages": [message.model_dump(mode="json") for message in request.messages],
            "stream": False,
            "options": options,
        }

    def _response(self, data: dict[str, Any], request: LLMRequest, latency: int) -> LLMResponse:
        try:
            text = str(data["message"]["content"])
        except (KeyError, TypeError) as exc:
            raise ProviderError(
                self.name,
                ProviderErrorCategory.STRUCTURED_OUTPUT,
                "Ollama response did not contain message content",
            ) from exc
        return LLMResponse(
            text=text,
            provider=self.name,
            model=str(data.get("model", request.model)),
            usage=normalized_usage(data.get("prompt_eval_count"), data.get("eval_count")),
            latency_ms=latency,
            raw_finish_reason=str(data.get("done_reason", "stop")),
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        data, latency, _ = await self._request(
            "POST",
            "/api/chat",
            json_body=self._body(request),
            timeout_seconds=request.timeout_seconds,
        )
        return self._response(data, request, latency)

    async def generate_structured(self, request: StructuredLLMRequest) -> StructuredLLMResponse:
        body = self._body(request)
        body["format"] = request.output_schema
        data, latency, _ = await self._request(
            "POST", "/api/chat", json_body=body, timeout_seconds=request.timeout_seconds
        )
        response = self._response(data, request, latency)
        return StructuredLLMResponse(
            **response.model_dump(), parsed=parse_json_text(self.name, response.text)
        )
