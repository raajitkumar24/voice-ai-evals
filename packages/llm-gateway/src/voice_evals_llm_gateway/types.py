from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class GatewayModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MessageRole(StrEnum):
    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(GatewayModel):
    role: MessageRole
    content: str


class LLMRequest(GatewayModel):
    model: str
    messages: list[LLMMessage]
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, ge=0, le=1)
    max_output_tokens: int = Field(default=2048, ge=1)
    timeout_seconds: float = Field(default=60, gt=0)
    metadata: dict[str, str] = Field(default_factory=dict)


class StructuredLLMRequest(LLMRequest):
    output_schema: dict[str, Any]
    schema_name: str = "eval_result"


class ProviderCapabilities(GatewayModel):
    structured_output: bool
    json_mode: bool = True
    long_context: bool = True
    multilingual: bool = True
    tool_calling: bool = False
    vision: bool = False
    streaming: bool = False


class ModelInfo(GatewayModel):
    id: str
    display_name: str | None = None
    capabilities: ProviderCapabilities | None = None


class ProviderHealth(GatewayModel):
    healthy: bool
    provider: str
    message: str
    latency_ms: int | None = None


class NormalizedUsage(GatewayModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class LLMResponse(GatewayModel):
    text: str
    provider: str
    model: str
    usage: NormalizedUsage = Field(default_factory=NormalizedUsage)
    latency_ms: int = Field(ge=0)
    raw_finish_reason: str | None = None
    request_id: str | None = None


class StructuredLLMResponse(LLMResponse):
    parsed: dict[str, Any]


class ProviderErrorCategory(StrEnum):
    AUTHENTICATION = "AUTHENTICATION"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    TRANSIENT = "TRANSIENT"
    INVALID_REQUEST = "INVALID_REQUEST"
    STRUCTURED_OUTPUT = "STRUCTURED_OUTPUT"
    CAPABILITY = "CAPABILITY"
    UNKNOWN = "UNKNOWN"


class ProviderError(RuntimeError):
    def __init__(
        self,
        provider: str,
        category: ProviderErrorCategory,
        message: str,
        *,
        retryable: bool = False,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.category = category
        self.retryable = retryable
        self.status_code = status_code


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    async def test_connection(self) -> ProviderHealth: ...

    async def list_models(self) -> list[ModelInfo]: ...

    async def generate(self, request: LLMRequest) -> LLMResponse: ...

    async def generate_structured(self, request: StructuredLLMRequest) -> StructuredLLMResponse: ...

    def capabilities(self, model: str | None = None) -> ProviderCapabilities: ...


ProviderName = Literal["openai", "anthropic", "gemini", "openai-compatible", "ollama", "test"]
