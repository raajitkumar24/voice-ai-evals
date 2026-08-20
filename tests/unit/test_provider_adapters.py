import json

import httpx
import pytest
from voice_evals_llm_gateway import LLMMessage, MessageRole, StructuredLLMRequest
from voice_evals_llm_providers import (
    AnthropicProvider,
    GeminiProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    OpenAIProvider,
)

SCHEMA = {
    "type": "object",
    "properties": {"verdict": {"type": "string", "enum": ["PASS", "FAIL"]}},
    "required": ["verdict"],
    "additionalProperties": False,
}
REQUEST = StructuredLLMRequest(
    model="configured-model",
    messages=[LLMMessage(role=MessageRole.USER, content="Evaluate this trace")],
    output_schema=SCHEMA,
)


def mock_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_openai_responses_adapter_normalizes_structured_output() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url.path == "/v1/responses"
        assert body["text"]["format"]["type"] == "json_schema"
        return httpx.Response(
            200,
            json={
                "id": "resp-1",
                "model": "configured-model",
                "status": "completed",
                "output": [{"content": [{"type": "output_text", "text": '{"verdict":"PASS"}'}]}],
                "usage": {"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
            },
        )

    async with mock_client(handler) as client:
        response = await OpenAIProvider("secret", client=client).generate_structured(REQUEST)
    assert response.parsed == {"verdict": "PASS"}
    assert response.usage.total_tokens == 14


@pytest.mark.asyncio
async def test_anthropic_adapter_uses_output_config_and_normalizes_usage() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["output_config"]["format"]["type"] == "json_schema"
        return httpx.Response(
            200,
            json={
                "id": "msg-1",
                "model": "configured-model",
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": '{"verdict":"FAIL"}'}],
                "usage": {"input_tokens": 12, "output_tokens": 5},
            },
        )

    async with mock_client(handler) as client:
        response = await AnthropicProvider("secret", client=client).generate_structured(REQUEST)
    assert response.parsed["verdict"] == "FAIL"
    assert response.usage.total_tokens == 17


@pytest.mark.asyncio
async def test_gemini_adapter_uses_response_json_schema() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.headers["x-goog-api-key"] == "secret"
        assert body["generationConfig"]["responseJsonSchema"] == SCHEMA
        return httpx.Response(
            200,
            json={
                "modelVersion": "configured-model",
                "responseId": "gem-1",
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {"parts": [{"text": '{"verdict":"PASS"}'}]},
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 9,
                    "candidatesTokenCount": 3,
                    "totalTokenCount": 12,
                },
            },
        )

    async with mock_client(handler) as client:
        response = await GeminiProvider("secret", client=client).generate_structured(REQUEST)
    assert response.parsed["verdict"] == "PASS"


@pytest.mark.asyncio
async def test_openai_compatible_adapter_uses_chat_completions() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url.path == "/v1/chat/completions"
        assert body["response_format"]["type"] == "json_schema"
        return httpx.Response(
            200,
            json={
                "id": "chat-1",
                "model": "configured-model",
                "choices": [
                    {"finish_reason": "stop", "message": {"content": '{"verdict":"PASS"}'}}
                ],
                "usage": {"prompt_tokens": 8, "completion_tokens": 3, "total_tokens": 11},
            },
        )

    async with mock_client(handler) as client:
        provider = OpenAICompatibleProvider(base_url="https://example.test/v1", client=client)
        response = await provider.generate_structured(REQUEST)
    assert response.parsed["verdict"] == "PASS"


@pytest.mark.asyncio
async def test_ollama_adapter_uses_schema_format() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url.path == "/api/chat"
        assert body["format"] == SCHEMA
        return httpx.Response(
            200,
            json={
                "model": "configured-model",
                "message": {"content": '{"verdict":"PASS"}'},
                "done_reason": "stop",
                "prompt_eval_count": 7,
                "eval_count": 3,
            },
        )

    async with mock_client(handler) as client:
        response = await OllamaProvider(client=client).generate_structured(REQUEST)
    assert response.parsed["verdict"] == "PASS"
