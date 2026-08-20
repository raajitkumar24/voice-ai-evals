from datetime import UTC, datetime

from fastapi.testclient import TestClient
from voice_evals_api.main import app


def authenticated_client() -> TestClient:
    client = TestClient(app)
    client.__enter__()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "change-me-before-production"},
    )
    assert response.status_code == 200
    return client


def prepare_agent(client: TestClient) -> None:
    agent = client.put(
        "/api/v1/agents/demo-agent",
        json={"external_id": "demo-agent", "name": "Demo Agent"},
    )
    assert agent.status_code == 200
    configuration = client.put(
        "/api/v1/agents/demo-agent/configurations/demo-config-v1",
        json={
            "id": "demo-config-v1",
            "agent_id": "demo-agent",
            "version": "1",
            "prompt": "Be concise and never guarantee approval.",
            "model": {"provider": "openai", "model": "configured-model", "parameters": {}},
        },
    )
    assert configuration.status_code == 200


def trace_payload(conversation_id: str = "conv-ingestion-test") -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "conversation_id": conversation_id,
        "agent_id": "demo-agent",
        "agent_config_version_id": "demo-config-v1",
        "started_at": datetime.now(UTC).isoformat(),
        "language_summary": {
            "primary_language": "hi-Latn",
            "languages": ["hi-Latn", "en"],
            "code_switching": True,
        },
        "turns": [
            {
                "turn_id": "turn-1",
                "sequence": 1,
                "timestamp_ms": 0,
                "speaker": "CUSTOMER",
                "text_original": "Mera outstanding amount kitna hai?",
                "language": {"code": "hi-Latn", "confidence": 0.98, "code_switched": True},
            },
            {
                "turn_id": "turn-2",
                "sequence": 2,
                "timestamp_ms": 500,
                "speaker": "AGENT",
                "text_original": "I will check that securely.",
            },
        ],
    }


def test_trace_ingestion_is_idempotent_and_preserves_original_text() -> None:
    client = authenticated_client()
    try:
        prepare_agent(client)
        headers = {"Idempotency-Key": "trace-ingestion-test-key"}
        payload = trace_payload()
        first = client.post("/api/v1/ingestion/conversations", json=payload, headers=headers)
        assert first.status_code == 201
        assert first.json()["integration_maturity"] == "LEVEL_1_TRANSCRIPT"

        second = client.post("/api/v1/ingestion/conversations", json=payload, headers=headers)
        assert second.status_code == 201
        assert second.json()["created"] is False
        assert second.json()["conversation_id"] == first.json()["conversation_id"]

        detail = client.get("/api/v1/conversations/conv-ingestion-test")
        assert detail.status_code == 200
        assert detail.json()["turns"][0]["text_original"] == "Mera outstanding amount kitna hai?"
    finally:
        client.__exit__(None, None, None)


def test_batch_reports_invalid_item_without_losing_valid_item() -> None:
    client = authenticated_client()
    try:
        prepare_agent(client)
        payload = trace_payload("conv-batch-valid")
        batch = client.post(
            "/api/v1/ingestion/conversations/batch",
            json={"items": [payload, {"schema_version": "1.0", "conversation_id": "broken"}]},
            headers={"Idempotency-Key": "batch-ingestion-test-key"},
        )
        assert batch.status_code == 200
        assert batch.json()["accepted"] == 1
        assert batch.json()["rejected"] == 1
        assert client.get("/api/v1/conversations/conv-batch-valid").status_code == 200
    finally:
        client.__exit__(None, None, None)
