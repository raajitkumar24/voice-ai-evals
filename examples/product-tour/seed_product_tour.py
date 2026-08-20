"""Seed a deterministic, populated workspace for screenshots and product tours.

Run this only against a local API started with VOICE_EVALS_ENABLE_TEST_PROVIDER=true.
It deliberately uses the fixture judge so the tour is repeatable and incurs no cost.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

LANGUAGES = [
    ("en", "Is my loan definitely approved?", "Yes, your final approval is guaranteed."),
    ("hi", "क्या मेरा लोन पक्का मंज़ूर है?", "हाँ, आपका अंतिम अप्रूवल पक्का है।"),
    ("hi-Latn", "Kya final approval guaranteed hai?", "Haan, loan definitely approved hai."),
    ("ta", "எனது கடன் உறுதியாக அனுமதிக்கப்பட்டதா?", "ஆம், இறுதி அனுமதி உறுதி."),
    ("ml", "എന്റെ ലോൺ ഉറപ്പായി അംഗീകരിച്ചോ?", "അല്ല, രേഖകൾ പരിശോധിച്ച ശേഷമാണ് അന്തിമ തീരുമാനം."),
]


def result(
    verdict: str = "PASS",
    *,
    code: str | None = None,
    reason: str = "The response follows the policy and available evidence.",
    evidence_type: str = "TURN",
    evidence_id: str = "agent-turn",
    severity: str | None = None,
    confidence: float = 0.94,
) -> dict[str, Any]:
    return {
        "verdict": verdict,
        "confidence": confidence,
        "severity": severity or ("HIGH" if verdict == "FAIL" else "INFO"),
        "failure_code": code,
        "reason": reason,
        "evidence": [{"type": evidence_type, "id": evidence_id}],
    }


def trace(index: int) -> dict[str, Any]:
    language, customer_text, agent_text = LANGUAGES[index % len(LANGUAGES)]
    suffix = f"{index + 1:02d}"
    customer_turn = f"customer-{suffix}"
    agent_turn = f"agent-{suffix}"
    retrieval_id = f"retrieval-{suffix}"
    tool_call_id = f"eligibility-{suffix}"
    evaluations = {
        "response_quality": result(evidence_id=agent_turn),
        "grounding": result(evidence_id=agent_turn),
        "rag": result(evidence_type="RETRIEVAL_EVENT", evidence_id=retrieval_id),
        "tool_trajectory": result(evidence_type="TOOL_CALL", evidence_id=tool_call_id),
        "conversation": result(evidence_id=agent_turn),
    }

    failure = index % 8
    if failure in {0, 1}:
        evaluations["response_quality"] = result(
            "FAIL",
            code="GUARANTEED_APPROVAL",
            reason="The assistant guarantees a final lending decision before verification.",
            evidence_id=agent_turn,
            confidence=0.98,
        )
    elif failure == 2:
        evaluations["grounding"] = result(
            "FAIL",
            code="KNOWLEDGE_GAP_APPLICATION_FEES",
            reason="The fee claim is unsupported by the approved lending knowledge base.",
            evidence_type="CHUNK",
            evidence_id=f"fee-policy-{suffix}",
            severity="CRITICAL",
            confidence=0.97,
        )
    elif failure == 3:
        evaluations["rag"] = result(
            "FAIL",
            code="RETRIEVAL_MISS_APPROVAL_POLICY",
            reason="Retrieval did not surface the final-approval qualification policy.",
            evidence_type="RETRIEVAL_EVENT",
            evidence_id=retrieval_id,
            confidence=0.93,
        )
    elif failure == 4:
        evaluations["tool_trajectory"] = result(
            "FAIL",
            code="TOOL_RESULT_IGNORED",
            reason="The response contradicted the eligibility tool's preliminary-only result.",
            evidence_type="TOOL_CALL",
            evidence_id=tool_call_id,
            confidence=0.96,
        )
    elif failure == 5:
        evaluations["conversation"] = result(
            "FAIL",
            code="HANDOFF_REFUSED",
            reason="The assistant refused an explicit request to speak with a human specialist.",
            evidence_id=agent_turn,
            severity="MEDIUM",
            confidence=0.95,
        )

    # The Malayalam examples are intentionally healthy to make parity trends readable.
    if language == "ml":
        evaluations = {
            key: result(
                evidence_type="RETRIEVAL_EVENT"
                if key == "rag"
                else "TOOL_CALL"
                if key == "tool_trajectory"
                else "TURN",
                evidence_id=retrieval_id
                if key == "rag"
                else tool_call_id
                if key == "tool_trajectory"
                else agent_turn,
            )
            for key in evaluations
        }

    started_at = datetime(2026, 8, 18, 9, 0, tzinfo=UTC) + timedelta(minutes=index * 17)
    return {
        "schema_version": "1.0",
        "conversation_id": f"tour-call-{suffix}",
        "agent_id": "product-tour-loan-agent",
        "agent_config_version_id": "product-tour-config-v7",
        "started_at": started_at.isoformat(),
        "ended_at": (started_at + timedelta(minutes=3, seconds=12 + index)).isoformat(),
        "channel": "voice",
        "metadata": {
            "source": "product-tour",
            "campaign": "August personal-loan qualification",
            "risk_flags": ["regulated_decision"] if failure < 5 else [],
            "expected_evals": evaluations,
        },
        "language_summary": {
            "primary_language": language,
            "languages": [language, "en"] if language == "hi-Latn" else [language],
            "code_switching": language == "hi-Latn",
        },
        "turns": [
            {
                "turn_id": customer_turn,
                "sequence": 1,
                "timestamp_ms": 0,
                "speaker": "CUSTOMER",
                "text_original": customer_text,
                "language": {
                    "code": language,
                    "confidence": 0.98,
                    "code_switched": language == "hi-Latn",
                },
            },
            {
                "turn_id": agent_turn,
                "sequence": 2,
                "timestamp_ms": 820,
                "speaker": "AGENT",
                "text_original": agent_text,
                "language": {
                    "code": language,
                    "confidence": 0.97,
                    "code_switched": language == "hi-Latn",
                },
            },
        ],
        "retrieval_events": [
            {
                "retrieval_event_id": retrieval_id,
                "timestamp_ms": 310,
                "trigger_turn_id": customer_turn,
                "query_original": customer_text,
                "retriever": {"type": "hybrid", "top_k": 3, "threshold": 0.72},
                "chunks": [
                    {
                        "chunk_id": f"approval-policy-{suffix}",
                        "source_id": "product-tour-policy-v3",
                        "content": (
                            "Preliminary eligibility is not final approval. "
                            "Documents and risk checks must be completed."
                        ),
                        "rank": 1,
                        "score": round(0.91 - index * 0.01, 2),
                    }
                ],
            }
        ],
        "tool_calls": [
            {
                "tool_call_id": tool_call_id,
                "tool_definition_version_id": "product-tour-eligibility-v2",
                "trigger_turn_id": customer_turn,
                "timestamp_ms": 470,
                "arguments": {"monthly_income": 50000 + index * 2500},
                "argument_provenance": {
                    "monthly_income": {"source": "CUSTOMER_TURN", "turn_id": customer_turn}
                },
                "status": "SUCCESS",
                "result": {
                    "preliminary_eligible": True,
                    "final_approval": False,
                    "next_step": "document_verification",
                },
                "duration_ms": 142 + index * 4,
            }
        ],
        "outcome": {
            "goal_achieved": failure >= 6 or language == "ml",
            "disposition": "qualified_with_next_steps"
            if failure >= 6 or language == "ml"
            else "quality_review_required",
        },
    }


def require_ok(response: httpx.Response) -> dict[str, Any]:
    response.raise_for_status()
    return response.json() if response.content else {}


def seed(base_url: str) -> str:
    with httpx.Client(base_url=base_url, timeout=30) as client:
        require_ok(
            client.post(
                "/api/v1/auth/login",
                json={"email": "admin@example.com", "password": "change-me-before-production"},
            )
        )
        require_ok(
            client.put(
                "/api/v1/agents/product-tour-loan-agent",
                json={
                    "external_id": "product-tour-loan-agent",
                    "name": "Aster Loan Concierge",
                    "description": "Multilingual personal-loan qualification and support agent",
                },
            )
        )
        require_ok(
            client.put(
                "/api/v1/tool-definitions/product-tour-eligibility-v2",
                json={
                    "id": "product-tour-eligibility-v2",
                    "version": "2",
                    "name": "check_preliminary_eligibility",
                    "description": (
                        "Checks preliminary eligibility; never returns a final lending decision."
                    ),
                    "input_schema": {
                        "type": "object",
                        "properties": {"monthly_income": {"type": "number"}},
                        "required": ["monthly_income"],
                    },
                    "policy": {"read_only": True},
                },
            )
        )
        require_ok(
            client.put(
                "/api/v1/knowledge-sources/product-tour-policy-v3",
                json={
                    "external_id": "product-tour-policy-v3",
                    "version": "3",
                    "source_type": "MARKDOWN",
                    "title": "India Personal Loan Policy — August 2026",
                    "content": (
                        "# Approval policy\nPreliminary eligibility is not final approval. "
                        "Document verification and risk checks are mandatory. "
                        "There is no application fee."
                    ),
                    "metadata": {"region": "IN", "approved": True},
                },
            )
        )
        require_ok(
            client.put(
                "/api/v1/agents/product-tour-loan-agent/configurations/product-tour-config-v7",
                json={
                    "id": "product-tour-config-v7",
                    "agent_id": "product-tour-loan-agent",
                    "version": "7",
                    "prompt": (
                        "Give accurate, qualified answers in the caller's language. "
                        "Never guarantee approval. Respect human handoff requests."
                    ),
                    "model": {"provider": "openai", "model": "configurable-production-model"},
                    "tool_definition_version_ids": ["product-tour-eligibility-v2"],
                    "knowledge_source_version_ids": ["product-tour-policy-v3"],
                    "retrieval_config": {"strategy": "hybrid", "top_k": 3},
                },
            )
        )
        batch = require_ok(
            client.post(
                "/api/v1/ingestion/conversations/batch",
                headers={"Idempotency-Key": "product-tour-rich-sample-v1"},
                json={"items": [trace(index) for index in range(15)]},
            )
        )
        if batch["rejected"]:
            raise RuntimeError(f"Product tour ingestion rejected items: {batch}")
        provider = require_ok(
            client.post(
                "/api/v1/providers",
                json={
                    "name": "Deterministic product-tour judge",
                    "provider": "test",
                    "secret_source": "NONE",
                    "default_model": "fixture-model",
                },
            )
        )
        run = require_ok(
            client.post(
                "/api/v1/eval-runs",
                json={
                    "conversation_ids": [f"tour-call-{index + 1:02d}" for index in range(15)],
                    "provider_connection_id": provider["id"],
                    "model": "fixture-model",
                    "sampling_config": {"method": "all", "seed": "product-tour-v1"},
                },
            )
        )
        return str(run["id"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    run_id = seed(args.base_url.rstrip("/"))
    print(f"Product tour ready. Evaluation run: {run_id}")
