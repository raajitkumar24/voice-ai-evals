from voice_evals_connectors import VoiceTraceConnector
from voice_evals_eval_core.synthesis import deterministic_recommendation


def test_knowledge_gap_never_invents_business_content() -> None:
    recommendation = deterministic_recommendation(
        "KNOWLEDGE_GAP", "KNOWLEDGE_CONTENT", "Answer from verified knowledge only."
    )

    assert recommendation.change_type == "KB_GAP"
    assert recommendation.proposed_content is None
    assert recommendation.requires_business_fact_verification is True


def test_v1_connector_contract_has_no_production_write_method() -> None:
    public_methods = {name for name in VoiceTraceConnector.__dict__ if not name.startswith("_")}
    assert public_methods == {"normalize"}
    assert VoiceTraceConnector.__annotations__ == {"connector_id": "str"}
