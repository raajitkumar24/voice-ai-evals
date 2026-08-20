from __future__ import annotations

import json
from typing import Any

from voice_evals_llm_gateway import (
    LLMRequest,
    LLMResponse,
    ModelInfo,
    NormalizedUsage,
    ProviderCapabilities,
    ProviderHealth,
    StructuredLLMRequest,
    StructuredLLMResponse,
)


class TestLLMProvider:
    """Deterministic fixture provider; registry inclusion requires an explicit test/demo flag."""

    __test__ = False
    name = "test"

    def capabilities(self, model: str | None = None) -> ProviderCapabilities:
        return ProviderCapabilities(structured_output=True, tool_calling=True)

    async def test_connection(self) -> ProviderHealth:
        return ProviderHealth(
            healthy=True, provider=self.name, message="Deterministic test provider"
        )

    async def list_models(self) -> list[ModelInfo]:
        return [ModelInfo(id="fixture-model", display_name="Deterministic fixture model")]

    async def generate(self, request: LLMRequest) -> LLMResponse:
        text = request.metadata.get("test_response", "Deterministic test response")
        return LLMResponse(
            text=text,
            provider=self.name,
            model=request.model,
            usage=NormalizedUsage(input_tokens=10, output_tokens=5, total_tokens=15),
            latency_ms=1,
            raw_finish_reason="stop",
            request_id="test-request",
        )

    async def generate_structured(self, request: StructuredLLMRequest) -> StructuredLLMResponse:
        if "test_response" in request.metadata:
            parsed = json.loads(request.metadata["test_response"])
        else:
            parsed = self._example_for_schema(request.output_schema)
        response = await self.generate(request)
        response_data = response.model_dump()
        response_data["text"] = json.dumps(parsed, ensure_ascii=False)
        return StructuredLLMResponse(**response_data, parsed=parsed)

    def _example_for_schema(self, schema: dict[str, Any]) -> Any:
        if "default" in schema:
            return schema["default"]
        if "enum" in schema:
            return schema["enum"][0]
        schema_type = schema.get("type")
        if schema_type == "object":
            return {
                name: self._example_for_schema(value)
                for name, value in schema.get("properties", {}).items()
                if name in schema.get("required", [])
            }
        if schema_type == "array":
            return []
        if schema_type == "string":
            return "fixture"
        if schema_type in {"number", "integer"}:
            return 0
        if schema_type == "boolean":
            return False
        return None
