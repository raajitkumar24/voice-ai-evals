from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from voice_evals_schemas import (
    AgentConfigurationVersion as AgentConfigurationSchema,
)
from voice_evals_schemas import ConversationTrace, ToolDefinitionVersion

from ..db import get_db
from ..models import (
    Agent,
    AgentConfigurationVersion,
    Conversation,
    KnowledgeSourceVersion,
    RetrievalEventRecord,
    ToolCallRecord,
)
from ..models import (
    ToolDefinitionVersion as ToolDefinitionRecord,
)
from ..security import Principal, get_principal
from ..services.ingestion import IngestionResult, canonical_hash, ingest_trace
from ..services.rate_limit import ingestion_rate_limit

router = APIRouter(tags=["ingestion"])


class AgentUpsert(BaseModel):
    external_id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class AgentView(AgentUpsert):
    id: str


class IngestionView(BaseModel):
    conversation_id: str
    external_id: str
    created: bool
    integration_maturity: str


class BatchIngestion(BaseModel):
    items: list[dict[str, Any]] = Field(min_length=1, max_length=1000)


class BatchItemResult(BaseModel):
    index: int
    ok: bool
    result: IngestionView | None = None
    error: dict[str, Any] | None = None


class BatchResult(BaseModel):
    accepted: int
    rejected: int
    items: list[BatchItemResult]


class KnowledgeSourceUpsert(BaseModel):
    external_id: str
    version: str
    source_type: str
    title: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def ingestion_view(result: IngestionResult) -> IngestionView:
    return IngestionView(
        conversation_id=result.conversation_id,
        external_id=result.external_id,
        created=result.created,
        integration_maturity=result.maturity.value,
    )


@router.put("/agents/{external_id}", response_model=AgentView)
def upsert_agent(
    external_id: str,
    payload: AgentUpsert,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> AgentView:
    if external_id != payload.external_id:
        raise HTTPException(status_code=422, detail="Path and payload external IDs must match")
    agent = db.scalar(
        select(Agent).where(
            Agent.workspace_id == principal.workspace_id, Agent.external_id == external_id
        )
    )
    if not agent:
        agent = Agent(workspace_id=principal.workspace_id, **payload.model_dump())
        db.add(agent)
    else:
        agent.name = payload.name
        agent.description = payload.description
    db.commit()
    db.refresh(agent)
    return AgentView(id=agent.id, **payload.model_dump())


@router.put(
    "/agents/{agent_external_id}/configurations/{configuration_id}",
    response_model=dict[str, Any],
)
def upsert_agent_configuration(
    agent_external_id: str,
    configuration_id: str,
    payload: AgentConfigurationSchema,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if payload.id != configuration_id or payload.agent_id != agent_external_id:
        raise HTTPException(status_code=422, detail="Configuration identifiers do not match path")
    agent = db.scalar(
        select(Agent).where(
            Agent.workspace_id == principal.workspace_id,
            Agent.external_id == agent_external_id,
        )
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    incoming = payload.model_dump(mode="json")
    existing = db.scalar(
        select(AgentConfigurationVersion).where(
            AgentConfigurationVersion.workspace_id == principal.workspace_id,
            AgentConfigurationVersion.external_id == configuration_id,
        )
    )
    if existing:
        persisted = {
            "id": existing.external_id,
            "agent_id": agent_external_id,
            "version": existing.version,
            "prompt": existing.prompt,
            "model": existing.model_config_data,
            "tool_definition_version_ids": existing.tool_definition_version_ids,
            "knowledge_source_version_ids": existing.knowledge_source_version_ids,
            "retrieval_config": existing.retrieval_config,
            "created_at": existing.created_at.isoformat(),
        }
        comparable_incoming = {**incoming, "created_at": persisted["created_at"]}
        if canonical_hash(persisted) != canonical_hash(comparable_incoming):
            raise HTTPException(
                status_code=409,
                detail="Agent configuration versions are immutable; create a new version",
            )
        return persisted
    record = AgentConfigurationVersion(
        workspace_id=principal.workspace_id,
        agent_id=agent.id,
        external_id=configuration_id,
        version=payload.version,
        prompt=payload.prompt,
        model_config_data=payload.model.model_dump(mode="json"),
        tool_definition_version_ids=payload.tool_definition_version_ids,
        knowledge_source_version_ids=payload.knowledge_source_version_ids,
        retrieval_config=payload.retrieval_config,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {**incoming, "created_at": record.created_at.isoformat()}


@router.put("/tool-definitions/{definition_id}", response_model=dict[str, Any])
def upsert_tool_definition(
    definition_id: str,
    payload: ToolDefinitionVersion,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if payload.id != definition_id:
        raise HTTPException(status_code=422, detail="Tool definition ID does not match path")
    existing = db.scalar(
        select(ToolDefinitionRecord).where(
            ToolDefinitionRecord.workspace_id == principal.workspace_id,
            ToolDefinitionRecord.external_id == definition_id,
            ToolDefinitionRecord.version == payload.version,
        )
    )
    incoming = payload.model_dump(mode="json")
    if existing:
        persisted = {
            "id": existing.external_id,
            "version": existing.version,
            "name": existing.name,
            "description": existing.description,
            "input_schema": existing.input_schema,
            "policy": existing.policy,
        }
        if canonical_hash(incoming) != canonical_hash(persisted):
            raise HTTPException(status_code=409, detail="Tool definition versions are immutable")
        return persisted
    db.add(
        ToolDefinitionRecord(
            workspace_id=principal.workspace_id,
            external_id=payload.id,
            version=payload.version,
            name=payload.name,
            description=payload.description,
            input_schema=payload.input_schema,
            policy=payload.policy,
        )
    )
    db.commit()
    return incoming


@router.put("/knowledge-sources/{source_id}", response_model=dict[str, Any])
def upsert_knowledge_source(
    source_id: str,
    payload: KnowledgeSourceUpsert,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if source_id != payload.external_id:
        raise HTTPException(status_code=422, detail="Knowledge source ID does not match path")
    content_hash = hashlib.sha256(payload.content.encode()).hexdigest()
    existing = db.scalar(
        select(KnowledgeSourceVersion).where(
            KnowledgeSourceVersion.workspace_id == principal.workspace_id,
            KnowledgeSourceVersion.external_id == source_id,
            KnowledgeSourceVersion.version == payload.version,
        )
    )
    if existing:
        if existing.content_hash != content_hash:
            raise HTTPException(status_code=409, detail="Knowledge source versions are immutable")
        return {**payload.model_dump(exclude={"content"}), "content_hash": content_hash}
    db.add(
        KnowledgeSourceVersion(
            workspace_id=principal.workspace_id,
            external_id=source_id,
            version=payload.version,
            source_type=payload.source_type,
            title=payload.title,
            content_hash=content_hash,
            parsed_text=payload.content,
            source_metadata=payload.metadata,
        )
    )
    db.commit()
    return {**payload.model_dump(exclude={"content"}), "content_hash": content_hash}


@router.post(
    "/ingestion/conversations",
    response_model=IngestionView,
    status_code=status.HTTP_201_CREATED,
)
def ingest_conversation(
    trace: ConversationTrace,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=200),
    principal: Principal = Depends(get_principal),
    _: None = Depends(ingestion_rate_limit),
    db: Session = Depends(get_db),
) -> IngestionView:
    result = ingest_trace(db, principal.workspace_id, trace, idempotency_key)
    return ingestion_view(result)


@router.post("/ingestion/conversations/batch", response_model=BatchResult)
def ingest_conversation_batch(
    payload: BatchIngestion,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=200),
    principal: Principal = Depends(get_principal),
    _: None = Depends(ingestion_rate_limit),
    db: Session = Depends(get_db),
) -> BatchResult:
    item_results: list[BatchItemResult] = []
    accepted = 0
    for index, item in enumerate(payload.items):
        try:
            trace = ConversationTrace.model_validate(item)
            item_key = f"{idempotency_key}:{index}"
            result = ingestion_view(ingest_trace(db, principal.workspace_id, trace, item_key))
            item_results.append(BatchItemResult(index=index, ok=True, result=result))
            accepted += 1
        except ValidationError as exc:
            db.rollback()
            item_results.append(
                BatchItemResult(
                    index=index, ok=False, error={"type": "validation", "details": exc.errors()}
                )
            )
        except HTTPException as exc:
            db.rollback()
            item_results.append(
                BatchItemResult(
                    index=index,
                    ok=False,
                    error={"type": "ingestion", "status": exc.status_code, "detail": exc.detail},
                )
            )
    return BatchResult(
        accepted=accepted,
        rejected=len(payload.items) - accepted,
        items=item_results,
    )


@router.get("/conversations", response_model=list[dict[str, Any]])
def list_conversations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    records = db.scalars(
        select(Conversation)
        .where(
            Conversation.workspace_id == principal.workspace_id, Conversation.deleted_at.is_(None)
        )
        .order_by(Conversation.started_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [
        {
            "id": record.id,
            "conversation_id": record.external_id,
            "started_at": record.started_at,
            "ended_at": record.ended_at,
            "language_summary": record.language_summary,
            "metadata": record.trace_metadata,
            "outcome": record.outcome,
        }
        for record in records
    ]


@router.get("/conversations/{conversation_id}", response_model=dict[str, Any])
def get_conversation(
    conversation_id: str,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.workspace_id == principal.workspace_id,
            (Conversation.id == conversation_id) | (Conversation.external_id == conversation_id),
            Conversation.deleted_at.is_(None),
        )
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    retrievals = db.scalars(
        select(RetrievalEventRecord).where(
            RetrievalEventRecord.conversation_id == conversation.id,
            RetrievalEventRecord.workspace_id == principal.workspace_id,
        )
    ).all()
    tool_calls = db.scalars(
        select(ToolCallRecord).where(
            ToolCallRecord.conversation_id == conversation.id,
            ToolCallRecord.workspace_id == principal.workspace_id,
        )
    ).all()
    return {
        "id": conversation.id,
        "conversation_id": conversation.external_id,
        "schema_version": conversation.schema_version,
        "started_at": conversation.started_at,
        "ended_at": conversation.ended_at,
        "channel": conversation.channel,
        "metadata": conversation.trace_metadata,
        "language_summary": conversation.language_summary,
        "outcome": conversation.outcome,
        "turns": [
            {
                "turn_id": turn.external_id,
                "sequence": turn.sequence,
                "timestamp_ms": turn.timestamp_ms,
                "speaker": turn.speaker,
                "text_original": turn.text_original,
                "language": turn.language,
                "translation": turn.translation,
            }
            for turn in conversation.turns
        ],
        "retrieval_events": [
            {
                "retrieval_event_id": item.external_id,
                "timestamp_ms": item.timestamp_ms,
                "trigger_turn_id": item.trigger_turn_id,
                "query_original": item.query_original,
                "query_rewritten": item.query_rewritten,
                "retriever": item.retriever,
                "chunks": item.chunks,
            }
            for item in retrievals
        ],
        "tool_calls": [
            {
                "tool_call_id": item.external_id,
                "tool_definition_version_id": item.tool_definition_version_id,
                "trigger_turn_id": item.trigger_turn_id,
                "timestamp_ms": item.timestamp_ms,
                "arguments": item.arguments,
                "argument_provenance": item.argument_provenance,
                "status": item.status,
                "result": item.result,
                "duration_ms": item.duration_ms,
            }
            for item in tool_calls
        ],
    }
