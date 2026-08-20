from datetime import UTC, datetime

import httpx
from voice_evals_sdk import VoiceEvalsClient


def test_sdk_validates_trace_and_sends_workspace_key() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            201,
            json={
                "conversation_id": "internal-id",
                "external_id": "sdk-conversation",
                "created": True,
                "integration_maturity": "LEVEL_1_TRANSCRIPT",
            },
        )

    trace = {
        "schema_version": "1.0",
        "conversation_id": "sdk-conversation",
        "agent_id": "sdk-agent",
        "agent_config_version_id": "sdk-config-v1",
        "started_at": datetime.now(UTC).isoformat(),
        "turns": [
            {
                "turn_id": "turn-1",
                "sequence": 1,
                "timestamp_ms": 0,
                "speaker": "CUSTOMER",
                "text_original": "Hello",
            }
        ],
    }
    with VoiceEvalsClient(
        "https://evals.example",
        "ve_secret",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.ingest_conversation(trace)

    assert result["created"] is True
    assert captured[0].headers["Authorization"] == "Bearer ve_secret"
    assert captured[0].headers["Idempotency-Key"]
