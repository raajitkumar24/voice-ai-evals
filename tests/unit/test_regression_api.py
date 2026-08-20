from datetime import UTC, datetime

from fastapi.testclient import TestClient
from voice_evals_api.main import app


def _judge(verdict: str, failure_code: str | None = None) -> dict[str, object]:
    return {
        "verdict": verdict,
        "confidence": 0.95,
        "severity": "HIGH" if verdict == "FAIL" else "INFO",
        "failure_code": failure_code,
        "reason": "Regression fixture result.",
        "evidence": [{"type": "TURN", "id": "agent-turn"}],
    }


def _trace(conversation_id: str, response_verdict: str) -> dict[str, object]:
    failure_code = "GUARANTEED_APPROVAL" if response_verdict == "FAIL" else None
    return {
        "schema_version": "1.0",
        "conversation_id": conversation_id,
        "agent_id": "regression-agent",
        "agent_config_version_id": "regression-config-v1",
        "started_at": datetime.now(UTC).isoformat(),
        "language_summary": {"primary_language": "en", "languages": ["en"]},
        "metadata": {
            "regression_case_id": "approval-case-1",
            "expected_evals": {
                "response_quality": _judge(response_verdict, failure_code),
                "grounding": _judge("PASS"),
                "conversation": _judge("PASS"),
            },
        },
        "turns": [
            {
                "turn_id": "customer-turn",
                "sequence": 1,
                "timestamp_ms": 0,
                "speaker": "CUSTOMER",
                "text_original": "Is approval guaranteed?",
            },
            {
                "turn_id": "agent-turn",
                "sequence": 2,
                "timestamp_ms": 100,
                "speaker": "AGENT",
                "text_original": "Response generated under the tested configuration.",
            },
        ],
    }


def test_regression_comparison_surfaces_fixed_case() -> None:
    with TestClient(app) as client:
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": "admin@example.com", "password": "change-me-before-production"},
            ).status_code
            == 200
        )
        assert (
            client.put(
                "/api/v1/agents/regression-agent",
                json={"external_id": "regression-agent", "name": "Regression Agent"},
            ).status_code
            == 200
        )
        assert (
            client.put(
                "/api/v1/agents/regression-agent/configurations/regression-config-v1",
                json={
                    "id": "regression-config-v1",
                    "agent_id": "regression-agent",
                    "version": "1",
                    "prompt": "Never guarantee approval.",
                    "model": {"provider": "test", "model": "fixture-model"},
                },
            ).status_code
            == 200
        )
        for conversation_id, verdict in [
            ("regression-baseline", "FAIL"),
            ("regression-candidate", "PASS"),
        ]:
            assert (
                client.post(
                    "/api/v1/ingestion/conversations",
                    json=_trace(conversation_id, verdict),
                    headers={"Idempotency-Key": conversation_id},
                ).status_code
                == 201
            )
        connection = client.post(
            "/api/v1/providers",
            json={"name": "Regression judge", "provider": "test", "secret_source": "NONE"},
        ).json()

        run_ids: list[str] = []
        for conversation_id in ["regression-baseline", "regression-candidate"]:
            response = client.post(
                "/api/v1/eval-runs",
                json={
                    "conversation_ids": [conversation_id],
                    "provider_connection_id": connection["id"],
                    "model": "fixture-model",
                },
            )
            assert response.status_code == 202
            assert response.json()["status"] == "COMPLETED"
            run_ids.append(response.json()["id"])

        candidate_patch = client.post(
            "/api/v1/candidate-patches",
            json={
                "change_type": "PROMPT_PATCH",
                "target": {"type": "AGENT_PROMPT"},
                "patch": {"proposed_content": "Never guarantee final approval."},
            },
        )
        assert candidate_patch.status_code == 201
        regression = client.post(
            "/api/v1/regression-runs",
            json={
                "candidate_patch_id": candidate_patch.json()["id"],
                "baseline_eval_run_id": run_ids[0],
                "candidate_eval_run_id": run_ids[1],
            },
        )
        assert regression.status_code == 201
        assert regression.json()["summary"]["fixed"] == 1
        assert regression.json()["summary"]["new_regressions"] == 0
        assert regression.json()["safe_to_export"] is True
