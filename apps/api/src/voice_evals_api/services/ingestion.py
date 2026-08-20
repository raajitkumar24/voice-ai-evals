from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from voice_evals_schemas import ConversationTrace, IntegrationMaturity

from ..models import (
    Agent,
    AgentConfigurationVersion,
    Conversation,
    RawIngestionEnvelope,
    RetrievalEventRecord,
    ToolCallRecord,
    TurnRecord,
)


def canonical_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode()).hexdigest()


def maturity_for_trace(trace: ConversationTrace) -> IntegrationMaturity:
    if trace.tool_calls:
        return IntegrationMaturity.LEVEL_3
    if trace.retrieval_events:
        return IntegrationMaturity.LEVEL_2
    return IntegrationMaturity.LEVEL_1


@dataclass(frozen=True)
class IngestionResult:
    conversation_id: str
    external_id: str
    created: bool
    maturity: IntegrationMaturity


def ingest_trace(
    db: Session,
    workspace_id: str,
    trace: ConversationTrace,
    idempotency_key: str,
) -> IngestionResult:
    payload = trace.model_dump(mode="json")
    payload_hash = canonical_hash(payload)
    prior_envelope = db.scalar(
        select(RawIngestionEnvelope).where(
            RawIngestionEnvelope.workspace_id == workspace_id,
            RawIngestionEnvelope.endpoint == "conversation_trace",
            RawIngestionEnvelope.idempotency_key == idempotency_key,
        )
    )
    if prior_envelope:
        if prior_envelope.payload_hash != payload_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key was already used with a different payload",
            )
        conversation = db.get(Conversation, prior_envelope.canonical_entity_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotent ingestion record exists without its canonical entity",
            )
        return IngestionResult(
            conversation.id,
            conversation.external_id,
            False,
            maturity_for_trace(trace),
        )

    existing = db.scalar(
        select(Conversation).where(
            Conversation.workspace_id == workspace_id,
            Conversation.external_id == trace.conversation_id,
        )
    )
    if existing:
        if existing.source_hash != payload_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conversation traces are immutable; use a new external conversation ID",
            )
        return IngestionResult(existing.id, existing.external_id, False, maturity_for_trace(trace))

    agent = db.scalar(
        select(Agent).where(
            Agent.workspace_id == workspace_id,
            Agent.external_id == trace.agent_id,
        )
    )
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Agent '{trace.agent_id}' must be registered before ingesting traces",
        )
    configuration = db.scalar(
        select(AgentConfigurationVersion).where(
            AgentConfigurationVersion.workspace_id == workspace_id,
            AgentConfigurationVersion.external_id == trace.agent_config_version_id,
            AgentConfigurationVersion.agent_id == agent.id,
        )
    )
    if not configuration:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Agent configuration '{trace.agent_config_version_id}' is not registered",
        )

    conversation = Conversation(
        workspace_id=workspace_id,
        external_id=trace.conversation_id,
        agent_id=agent.id,
        agent_config_version_id=configuration.id,
        schema_version=trace.schema_version,
        started_at=trace.started_at,
        ended_at=trace.ended_at,
        channel=trace.channel,
        trace_metadata=trace.metadata,
        language_summary=trace.language_summary.model_dump(mode="json"),
        outcome=trace.outcome.model_dump(mode="json") if trace.outcome else None,
        source_hash=payload_hash,
    )
    db.add(conversation)
    db.flush()
    for turn in trace.turns:
        db.add(
            TurnRecord(
                workspace_id=workspace_id,
                conversation_id=conversation.id,
                external_id=turn.turn_id,
                sequence=turn.sequence,
                timestamp_ms=turn.timestamp_ms,
                speaker=turn.speaker.value,
                text_original=turn.text_original,
                language=turn.language.model_dump(mode="json") if turn.language else None,
                translation=turn.translation.model_dump(mode="json") if turn.translation else None,
            )
        )
    for event in trace.retrieval_events:
        db.add(
            RetrievalEventRecord(
                workspace_id=workspace_id,
                conversation_id=conversation.id,
                external_id=event.retrieval_event_id,
                timestamp_ms=event.timestamp_ms,
                trigger_turn_id=event.trigger_turn_id,
                query_original=event.query_original,
                query_rewritten=event.query_rewritten,
                retriever=event.retriever.model_dump(mode="json"),
                chunks=[chunk.model_dump(mode="json") for chunk in event.chunks],
            )
        )
    for tool_call in trace.tool_calls:
        db.add(
            ToolCallRecord(
                workspace_id=workspace_id,
                conversation_id=conversation.id,
                external_id=tool_call.tool_call_id,
                tool_definition_version_id=tool_call.tool_definition_version_id,
                trigger_turn_id=tool_call.trigger_turn_id,
                timestamp_ms=tool_call.timestamp_ms,
                arguments=tool_call.arguments,
                argument_provenance={
                    key: source.model_dump(mode="json")
                    for key, source in tool_call.argument_provenance.items()
                },
                status=tool_call.status.value,
                result=tool_call.result,
                duration_ms=tool_call.duration_ms,
            )
        )
    envelope = RawIngestionEnvelope(
        workspace_id=workspace_id,
        endpoint="conversation_trace",
        idempotency_key=idempotency_key,
        payload_hash=payload_hash,
        payload=payload,
        status="NORMALIZED",
        canonical_entity_id=conversation.id,
    )
    db.add(envelope)
    db.commit()
    return IngestionResult(
        conversation.id, conversation.external_id, True, maturity_for_trace(trace)
    )
