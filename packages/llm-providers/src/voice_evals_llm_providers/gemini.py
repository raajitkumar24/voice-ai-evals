from __future__ import annotations

from typing import Any
from urllib.parse import quote

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


class GeminiProvider(HTTPProviderBase):
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(base_url=base_url, api_key=api_key, client=client)

    @property
    def headers(self) -> dict[str, str]:
        return {"x-goog-api-key": str(self.api_key), "Content-Type": "application/json"}

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
            ModelInfo(
                id=str(item["name"]).removeprefix("models/"), display_name=item.get("displayName")
            )
            for item in data.get("models", [])
            if isinstance(item, dict) and item.get("name")
        ]

    def _body(self, request: LLMRequest) -> dict[str, Any]:
        system_parts: list[str] = []
        contents: list[dict[str, Any]] = []
        for message in request.messages:
            if message.role in {MessageRole.SYSTEM, MessageRole.DEVELOPER}:
                system_parts.append(message.content)
            else:
                role = "model" if message.role == MessageRole.ASSISTANT else "user"
                contents.append({"role": role, "parts": [{"text": message.content}]})
        generation_config: dict[str, Any] = {"maxOutputTokens": request.max_output_tokens}
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature
        if request.top_p is not None:
            generation_config["topP"] = request.top_p
        body: dict[str, Any] = {"contents": contents, "generationConfig": generation_config}
        if system_parts:
            body["system_instruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
        return body

    @staticmethod
    def _text(data: dict[str, Any]) -> str:
        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                "gemini",
                ProviderErrorCategory.STRUCTURED_OUTPUT,
                "Gemini response did not contain candidate text",
            ) from exc

    async def _generate_data(
        self, request: LLMRequest, body: dict[str, Any]
    ) -> tuple[dict[str, Any], int, str | None]:
        model = quote(request.model.removeprefix("models/"), safe="-._")
        return await self._request(
            "POST",
            f"/models/{model}:generateContent",
            headers=self.headers,
            json_body=body,
            timeout_seconds=request.timeout_seconds,
        )

    def _response(
        self, data: dict[str, Any], request: LLMRequest, latency: int, request_id: str | None
    ) -> LLMResponse:
        usage = data.get("usageMetadata", {})
        candidates = data.get("candidates") or [{}]
        return LLMResponse(
            text=self._text(data),
            provider=self.name,
            model=str(data.get("modelVersion", request.model)),
            usage=normalized_usage(
                usage.get("promptTokenCount"),
                usage.get("candidatesTokenCount"),
                usage.get("totalTokenCount"),
            ),
            latency_ms=latency,
            raw_finish_reason=candidates[0].get("finishReason")
            if isinstance(candidates[0], dict)
            else None,
            request_id=request_id or data.get("responseId"),
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        data, latency, request_id = await self._generate_data(request, self._body(request))
        return self._response(data, request, latency, request_id)

    async def generate_structured(self, request: StructuredLLMRequest) -> StructuredLLMResponse:
        body = self._body(request)
        body["generationConfig"].update(
            {"responseMimeType": "application/json", "responseJsonSchema": request.output_schema}
        )
        data, latency, request_id = await self._generate_data(request, body)
        response = self._response(data, request, latency, request_id)
        return StructuredLLMResponse(
            **response.model_dump(), parsed=parse_json_text(self.name, response.text)
        )
