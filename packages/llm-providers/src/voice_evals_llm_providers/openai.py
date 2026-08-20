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


class OpenAIProvider(HTTPProviderBase):
    name = "openai"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.openai.com/v1",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(base_url=base_url, api_key=api_key, client=client)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

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
            ModelInfo(id=item["id"])
            for item in data.get("data", [])
            if isinstance(item, dict) and item.get("id")
        ]

    def _body(self, request: LLMRequest) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": request.model,
            "input": [message.model_dump(mode="json") for message in request.messages],
            "max_output_tokens": request.max_output_tokens,
        }
        if request.temperature is not None:
            body["temperature"] = request.temperature
        if request.top_p is not None:
            body["top_p"] = request.top_p
        return body

    @staticmethod
    def _text(data: dict[str, Any]) -> str:
        if isinstance(data.get("output_text"), str):
            return str(data["output_text"])
        for output in data.get("output", []):
            if not isinstance(output, dict):
                continue
            for content in output.get("content", []):
                if isinstance(content, dict) and content.get("type") == "output_text":
                    return str(content.get("text", ""))
        raise ProviderError(
            "openai",
            ProviderErrorCategory.STRUCTURED_OUTPUT,
            "OpenAI response did not contain output text",
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        data, latency, request_id = await self._request(
            "POST",
            "/responses",
            headers=self.headers,
            json_body=self._body(request),
            timeout_seconds=request.timeout_seconds,
        )
        usage = data.get("usage", {})
        return LLMResponse(
            text=self._text(data),
            provider=self.name,
            model=str(data.get("model", request.model)),
            usage=normalized_usage(
                usage.get("input_tokens"), usage.get("output_tokens"), usage.get("total_tokens")
            ),
            latency_ms=latency,
            raw_finish_reason=data.get("status"),
            request_id=request_id or data.get("id"),
        )

    async def generate_structured(self, request: StructuredLLMRequest) -> StructuredLLMResponse:
        body = self._body(request)
        body["text"] = {
            "format": {
                "type": "json_schema",
                "name": request.schema_name,
                "schema": request.output_schema,
                "strict": True,
            }
        }
        data, latency, request_id = await self._request(
            "POST",
            "/responses",
            headers=self.headers,
            json_body=body,
            timeout_seconds=request.timeout_seconds,
        )
        text = self._text(data)
        usage = data.get("usage", {})
        return StructuredLLMResponse(
            text=text,
            parsed=parse_json_text(self.name, text),
            provider=self.name,
            model=str(data.get("model", request.model)),
            usage=normalized_usage(
                usage.get("input_tokens"), usage.get("output_tokens"), usage.get("total_tokens")
            ),
            latency_ms=latency,
            raw_finish_reason=data.get("status"),
            request_id=request_id or data.get("id"),
        )
