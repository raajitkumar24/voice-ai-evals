from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from voice_evals_schemas import ConversationTrace, Speaker, Turn


def test_original_turn_round_trip_is_lossless() -> None:
    original = "Mera outstanding amount kitna hai?"
    trace = ConversationTrace(
        conversation_id="conv-1",
        agent_id="agent-1",
        agent_config_version_id="cfg-1",
        started_at=datetime.now(UTC),
        turns=[
            Turn(
                turn_id="turn-1",
                sequence=1,
                timestamp_ms=100,
                speaker=Speaker.CUSTOMER,
                text_original=original,
            )
        ],
    )
    restored = ConversationTrace.model_validate_json(trace.model_dump_json())
    assert restored.turns[0].text_original == original


def test_duplicate_turn_sequence_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ConversationTrace(
            conversation_id="conv-1",
            agent_id="agent-1",
            agent_config_version_id="cfg-1",
            started_at=datetime.now(UTC),
            turns=[
                Turn(
                    turn_id="a", sequence=1, timestamp_ms=0, speaker="CUSTOMER", text_original="a"
                ),
                Turn(turn_id="b", sequence=1, timestamp_ms=1, speaker="AGENT", text_original="b"),
            ],
        )
