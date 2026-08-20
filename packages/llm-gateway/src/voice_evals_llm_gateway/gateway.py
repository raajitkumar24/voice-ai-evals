from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from .types import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderError,
    ProviderErrorCategory,
    StructuredLLMRequest,
    StructuredLLMResponse,
)


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_backoff_seconds: float = 0.25
    max_backoff_seconds: float = 2.0


@dataclass
class ProviderRegistry:
    providers: dict[str, LLMProvider] = field(default_factory=dict)

    def register(self, provider: LLMProvider) -> None:
        self.providers[provider.name] = provider

    def get(self, name: str) -> LLMProvider:
        try:
            return self.providers[name]
        except KeyError as exc:
            raise ProviderError(
                name,
                ProviderErrorCategory.INVALID_REQUEST,
                f"Provider '{name}' is not registered",
            ) from exc


@dataclass(frozen=True)
class RoutingDecision:
    requested_provider: str
    executed_provider: str
    fallback_used: bool
    fallback_reason: str | None
    attempts: int


class LLMGateway:
    def __init__(self, registry: ProviderRegistry, retry_policy: RetryPolicy | None = None):
        self.registry = registry
        self.retry_policy = retry_policy or RetryPolicy()

    async def generate(
        self,
        provider_name: str,
        request: LLMRequest,
        *,
        fallback_provider: str | None = None,
    ) -> tuple[LLMResponse, RoutingDecision]:
        try:
            response, attempts = await self._with_retry(
                self.registry.get(provider_name), request, structured=False
            )
            return response, RoutingDecision(provider_name, provider_name, False, None, attempts)
        except ProviderError as primary_error:
            if not fallback_provider or primary_error.category not in {
                ProviderErrorCategory.RATE_LIMIT,
                ProviderErrorCategory.TIMEOUT,
                ProviderErrorCategory.TRANSIENT,
            }:
                raise
            response, attempts = await self._with_retry(
                self.registry.get(fallback_provider), request, structured=False
            )
            return response, RoutingDecision(
                provider_name,
                fallback_provider,
                True,
                primary_error.category.value,
                attempts,
            )

    async def generate_structured(
        self,
        provider_name: str,
        request: StructuredLLMRequest,
        *,
        fallback_provider: str | None = None,
    ) -> tuple[StructuredLLMResponse, RoutingDecision]:
        Draft202012Validator.check_schema(request.output_schema)
        try:
            response, attempts = await self._with_retry(
                self.registry.get(provider_name), request, structured=True
            )
            assert isinstance(response, StructuredLLMResponse)
            self._validate_structured(response, request)
            return response, RoutingDecision(provider_name, provider_name, False, None, attempts)
        except ProviderError as primary_error:
            if not fallback_provider or primary_error.category not in {
                ProviderErrorCategory.RATE_LIMIT,
                ProviderErrorCategory.TIMEOUT,
                ProviderErrorCategory.TRANSIENT,
                ProviderErrorCategory.STRUCTURED_OUTPUT,
            }:
                raise
            response, attempts = await self._with_retry(
                self.registry.get(fallback_provider), request, structured=True
            )
            assert isinstance(response, StructuredLLMResponse)
            self._validate_structured(response, request)
            return response, RoutingDecision(
                provider_name,
                fallback_provider,
                True,
                primary_error.category.value,
                attempts,
            )

    async def _with_retry(
        self,
        provider: LLMProvider,
        request: LLMRequest,
        *,
        structured: bool,
    ) -> tuple[LLMResponse, int]:
        backoff = self.retry_policy.initial_backoff_seconds
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                response: LLMResponse
                if structured:
                    assert isinstance(request, StructuredLLMRequest)
                    response = await provider.generate_structured(request)
                else:
                    response = await provider.generate(request)
                return response, attempt
            except ProviderError as exc:
                if not exc.retryable or attempt >= self.retry_policy.max_attempts:
                    raise
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.retry_policy.max_backoff_seconds)
        raise AssertionError("retry loop exhausted without a response or error")

    @staticmethod
    def _validate_structured(
        response: StructuredLLMResponse, request: StructuredLLMRequest
    ) -> None:
        try:
            Draft202012Validator(request.output_schema).validate(response.parsed)
        except ValidationError as exc:
            raise ProviderError(
                response.provider,
                ProviderErrorCategory.STRUCTURED_OUTPUT,
                f"Provider returned data that does not match the requested schema: {exc.message}",
                retryable=True,
            ) from exc
        try:
            json.dumps(response.parsed)
        except (TypeError, ValueError) as exc:
            raise ProviderError(
                response.provider,
                ProviderErrorCategory.STRUCTURED_OUTPUT,
                "Provider returned non-serializable structured output",
                retryable=True,
            ) from exc
