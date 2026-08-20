import pytest
from voice_evals_llm_gateway import (
    LLMGateway,
    LLMMessage,
    MessageRole,
    ProviderError,
    ProviderErrorCategory,
    ProviderRegistry,
    RetryPolicy,
    StructuredLLMRequest,
)
from voice_evals_llm_providers import TestLLMProvider


class RateLimitedTestProvider(TestLLMProvider):
    name = "rate-limited"

    async def generate_structured(self, request: StructuredLLMRequest):
        raise ProviderError(
            self.name,
            ProviderErrorCategory.RATE_LIMIT,
            "rate limited",
            retryable=False,
        )


@pytest.mark.asyncio
async def test_gateway_records_explicit_fallback_decision() -> None:
    registry = ProviderRegistry()
    registry.register(RateLimitedTestProvider())
    registry.register(TestLLMProvider())
    gateway = LLMGateway(registry, RetryPolicy(max_attempts=1))
    request = StructuredLLMRequest(
        model="fixture-model",
        messages=[LLMMessage(role=MessageRole.USER, content="evaluate")],
        output_schema={
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
        },
    )
    response, decision = await gateway.generate_structured(
        "rate-limited", request, fallback_provider="test"
    )
    assert response.parsed == {"ok": False}
    assert decision.fallback_used is True
    assert decision.fallback_reason == "RATE_LIMIT"
