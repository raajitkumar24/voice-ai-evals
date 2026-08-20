from datetime import UTC, datetime

from fastapi.testclient import TestClient
from voice_evals_api.main import app


def judge_result(failure_code: str | None = None) -> dict[str, object]:
    failed = failure_code is not None
    return {
        "verdict": "FAIL" if failed else "PASS",
        "confidence": 0.96,
        "severity": "HIGH" if failed else "INFO",
        "failure_code": failure_code,
        "reason": "Fixture-driven evaluator result.",
        "evidence": [{"type": "TURN", "id": "turn-agent"}],
    }


def test_eval_run_executes_specialists_and_records_provenance() -> None:
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
                "/api/v1/agents/eval-agent",
                json={"external_id": "eval-agent", "name": "Eval Agent"},
            ).status_code
            == 200
        )
        assert (
            client.put(
                "/api/v1/agents/eval-agent/configurations/eval-config-v1",
                json={
                    "id": "eval-config-v1",
                    "agent_id": "eval-agent",
                    "version": "1",
                    "prompt": "Never guarantee final approval.",
                    "model": {"provider": "test", "model": "fixture-model"},
                },
            ).status_code
            == 200
        )
        trace = {
            "schema_version": "1.0",
            "conversation_id": "eval-conversation",
            "agent_id": "eval-agent",
            "agent_config_version_id": "eval-config-v1",
            "started_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "expected_evals": {
                    "response_quality": judge_result("GUARANTEED_APPROVAL"),
                    "grounding": judge_result("CLAIM_UNSUPPORTED"),
                    "conversation": judge_result(),
                }
            },
            "turns": [
                {
                    "turn_id": "turn-customer",
                    "sequence": 1,
                    "timestamp_ms": 0,
                    "speaker": "CUSTOMER",
                    "text_original": "Will my loan definitely be approved?",
                },
                {
                    "turn_id": "turn-agent",
                    "sequence": 2,
                    "timestamp_ms": 500,
                    "speaker": "AGENT",
                    "text_original": "Yes, your final approval is guaranteed.",
                },
            ],
        }
        ingested = client.post(
            "/api/v1/ingestion/conversations",
            json=trace,
            headers={"Idempotency-Key": "eval-conversation-ingestion"},
        )
        assert ingested.status_code == 201
        connection = client.post(
            "/api/v1/providers",
            json={"name": "Fixture judge", "provider": "test", "secret_source": "NONE"},
        )
        assert connection.status_code == 201
        run = client.post(
            "/api/v1/eval-runs",
            json={
                "conversation_ids": ["eval-conversation"],
                "provider_connection_id": connection.json()["id"],
                "model": "fixture-model",
            },
        )
        assert run.status_code == 202
        assert run.json()["status"] == "COMPLETED"
        assert run.json()["counts"] == {
            "results": 5,
            "pass": 1,
            "fail": 2,
            "not_applicable": 2,
            "errors": 0,
        }
        results = client.get(f"/api/v1/eval-runs/{run.json()['id']}/results")
        assert results.status_code == 200
        failures = [item for item in results.json() if item["verdict"] == "FAIL"]
        assert {item["failure_code"] for item in failures} == {
            "GUARANTEED_APPROVAL",
            "CLAIM_UNSUPPORTED",
        }
        assert all(item["judge_provenance"]["provider"] == "test" for item in failures)

        findings = client.get("/api/v1/findings", params={"run_id": run.json()["id"]})
        assert findings.status_code == 200
        assert len(findings.json()) == 2
        assert all(item["synthesis_provenance"]["provider"] == "test" for item in findings.json())

        recommendations = client.get("/api/v1/recommendations")
        assert recommendations.status_code == 200
        generated = [
            item
            for item in recommendations.json()
            if item["finding_id"] in {finding["id"] for finding in findings.json()}
        ]
        assert len(generated) == 2
        prompt_patch = next(item for item in generated if item["change_type"] == "PROMPT_PATCH")
        blocked_export = client.post(
            f"/api/v1/recommendations/{prompt_patch['id']}/draft-artifacts"
        )
        assert blocked_export.status_code == 409

        approved = client.post(
            f"/api/v1/recommendations/{prompt_patch['id']}/reviews",
            json={"action": "APPROVE", "comment": "Evidence supports this draft."},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "APPROVED"
        artifact = client.post(f"/api/v1/recommendations/{prompt_patch['id']}/draft-artifacts")
        assert artifact.status_code == 201
        assert artifact.json()["content"]["draft_only"] is True
        assert artifact.json()["content"]["production_writeback_supported"] is False

        overview = client.get("/api/v1/analytics/overview", params={"run_id": run.json()["id"]})
        assert overview.status_code == 200
        assert overview.json()["metrics"]["eval_pass_rate"] == 0.3333
        assert overview.json()["metrics"]["eval_coverage"] == 0.6
