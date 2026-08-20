from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from voice_evals_eval_core import EvalDefinition, load_eval_definitions
from voice_evals_worker.tasks import execute_eval_run

from ..config import Settings, get_settings
from ..db import get_db
from ..models import (
    AuditEvent,
    Conversation,
    Dataset,
    EvalDefinitionRecord,
    EvalResultRecord,
    EvalRunRecord,
    EvalSuiteRecord,
    ProviderConnection,
)
from ..security import Principal, require_user

router = APIRouter(prefix="/eval-runs", tags=["evaluation runs"])


class SamplingConfig(BaseModel):
    method: Literal["all", "random", "stratified_language", "failed_outcome", "risk_based"] = "all"
    percentage: float | None = Field(default=None, gt=0, le=1)
    sample_size: int | None = Field(default=None, ge=1)
    seed: str = Field(default="voice-evals-v1", max_length=100)


class EvalRunCreate(BaseModel):
    conversation_ids: list[str] = Field(default_factory=list, max_length=10000)
    dataset_id: str | None = None
    provider_connection_id: str
    model: str = Field(min_length=1, max_length=200)
    sampling_config: SamplingConfig = Field(default_factory=SamplingConfig)
    suite_id: str | None = None

    @model_validator(mode="after")
    def exactly_one_source(self) -> EvalRunCreate:
        if bool(self.conversation_ids) == bool(self.dataset_id):
            raise ValueError("Provide exactly one of conversation_ids or dataset_id")
        return self


class EvalRunView(BaseModel):
    id: str
    status: str
    snapshot: dict[str, Any]
    sampling_config: dict[str, Any]
    counts: dict[str, Any]
    usage: dict[str, Any]
    warnings: list[Any]
    errors: list[Any]


def run_view(run: EvalRunRecord) -> EvalRunView:
    return EvalRunView(
        id=run.id,
        status=run.status,
        snapshot=run.snapshot,
        sampling_config=run.sampling_config,
        counts=run.counts,
        usage=run.usage,
        warnings=run.warnings,
        errors=run.errors,
    )


def _sample_conversations(
    conversations: list[Conversation], config: SamplingConfig
) -> list[Conversation]:
    if config.method == "all" and config.percentage is None and config.sample_size is None:
        return conversations
    target = config.sample_size or max(
        1, round(len(conversations) * (config.percentage if config.percentage else 1))
    )
    target = min(target, len(conversations))

    def rank(conversation: Conversation) -> str:
        return hashlib.sha256(f"{config.seed}:{conversation.id}".encode()).hexdigest()

    if config.method == "stratified_language":
        groups: dict[str, list[Conversation]] = defaultdict(list)
        for conversation in conversations:
            language = str(conversation.language_summary.get("primary_language") or "unknown")
            groups[language].append(conversation)
        selected: list[Conversation] = []
        for group in groups.values():
            quota = max(1, round(target * len(group) / len(conversations)))
            selected.extend(sorted(group, key=rank)[:quota])
        return sorted(selected, key=rank)[:target]
    if config.method == "failed_outcome":
        return sorted(
            conversations,
            key=lambda item: (
                item.outcome.get("goal_achieved") is not False if item.outcome else True,
                rank(item),
            ),
        )[:target]
    if config.method == "risk_based":
        return sorted(
            conversations,
            key=lambda item: (not bool(item.trace_metadata.get("risk_flags")), rank(item)),
        )[:target]
    return sorted(conversations, key=rank)[:target]


@router.post("", response_model=EvalRunView, status_code=status.HTTP_202_ACCEPTED)
def create_eval_run(
    payload: EvalRunCreate,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EvalRunView:
    connection = db.scalar(
        select(ProviderConnection).where(
            ProviderConnection.id == payload.provider_connection_id,
            ProviderConnection.workspace_id == principal.workspace_id,
        )
    )
    if not connection:
        raise HTTPException(status_code=404, detail="Provider connection not found")
    requested_conversation_ids = payload.conversation_ids
    dataset: Dataset | None = None
    if payload.dataset_id:
        dataset = db.scalar(
            select(Dataset).where(
                Dataset.id == payload.dataset_id,
                Dataset.workspace_id == principal.workspace_id,
            )
        )
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        requested_conversation_ids = [str(item) for item in dataset.conversation_ids]
        if not requested_conversation_ids:
            raise HTTPException(status_code=422, detail="Dataset contains no conversations")
    conversations = db.scalars(
        select(Conversation).where(
            Conversation.workspace_id == principal.workspace_id,
            Conversation.deleted_at.is_(None),
            (Conversation.id.in_(requested_conversation_ids))
            | (Conversation.external_id.in_(requested_conversation_ids)),
        )
    ).all()
    if len(conversations) != len(set(requested_conversation_ids)):
        raise HTTPException(status_code=404, detail="One or more conversations were not found")
    conversations = _sample_conversations(list(conversations), payload.sampling_config)
    if len(conversations) > settings.max_conversations_per_run:
        raise HTTPException(status_code=422, detail="Run exceeds the conversation safety limit")
    suite: EvalSuiteRecord | None = None
    if payload.suite_id:
        suite = db.scalar(
            select(EvalSuiteRecord).where(
                EvalSuiteRecord.id == payload.suite_id,
                EvalSuiteRecord.workspace_id == principal.workspace_id,
            )
        )
        if not suite:
            raise HTTPException(status_code=404, detail="Eval suite not found")
        definition_records = db.scalars(
            select(EvalDefinitionRecord).where(
                EvalDefinitionRecord.workspace_id == principal.workspace_id
            )
        ).all()
        by_identity = {
            f"{record.definition_id}:{record.version}": record for record in definition_records
        }
        missing = set(suite.definition_versions) - set(by_identity)
        if missing:
            raise HTTPException(status_code=409, detail="Eval suite references missing definitions")
        definitions = [
            EvalDefinition.model_validate(by_identity[identity].config)
            for identity in suite.definition_versions
        ]
    else:
        definitions = load_eval_definitions()
    estimated_calls = len(conversations) * len(
        [definition for definition in definitions if definition.scope == "CONVERSATION"]
    )
    if estimated_calls > settings.max_evaluator_calls_per_run:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Estimated evaluator calls ({estimated_calls}) exceed the deployment limit "
                f"({settings.max_evaluator_calls_per_run})"
            ),
        )
    run = EvalRunRecord(
        workspace_id=principal.workspace_id,
        dataset_id=dataset.id if dataset else None,
        suite_id=suite.id if suite else None,
        status="QUEUED",
        snapshot={
            "conversation_ids": [conversation.id for conversation in conversations],
            "conversation_source_hashes": {
                conversation.id: conversation.source_hash for conversation in conversations
            },
            "eval_definition_versions": [
                f"{definition.id}:{definition.version}" for definition in definitions
            ],
            "eval_definitions": [definition.model_dump(mode="json") for definition in definitions],
            "provider_connection_id": connection.id,
            "provider_configuration_version": connection.updated_at.isoformat(),
            "model": payload.model,
            "routing_profile_version": "inline-v1",
        },
        sampling_config=payload.sampling_config.model_dump(mode="json"),
        routing_profile={
            "provider_connection_id": connection.id,
            "provider": connection.provider,
            "model": payload.model,
        },
    )
    db.add(run)
    db.flush()
    db.add(
        AuditEvent(
            workspace_id=principal.workspace_id,
            actor_user_id=principal.user_id,
            event_type="eval_run.created",
            entity_type="eval_run",
            entity_id=run.id,
            event_data={
                "conversation_count": len(conversations),
                "estimated_evaluator_calls": estimated_calls,
                "sampling": payload.sampling_config.model_dump(mode="json"),
            },
        )
    )
    db.commit()
    db.refresh(run)
    execute_eval_run.delay(run.id)
    db.refresh(run)
    return run_view(run)


@router.get("", response_model=list[EvalRunView])
def list_eval_runs(
    principal: Principal = Depends(require_user), db: Session = Depends(get_db)
) -> list[EvalRunView]:
    runs = db.scalars(
        select(EvalRunRecord)
        .where(EvalRunRecord.workspace_id == principal.workspace_id)
        .order_by(EvalRunRecord.created_at.desc())
        .limit(100)
    ).all()
    return [run_view(run) for run in runs]


@router.get("/{run_id}", response_model=EvalRunView)
def get_eval_run(
    run_id: str,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> EvalRunView:
    run = db.scalar(
        select(EvalRunRecord).where(
            EvalRunRecord.id == run_id, EvalRunRecord.workspace_id == principal.workspace_id
        )
    )
    if not run:
        raise HTTPException(status_code=404, detail="Eval run not found")
    return run_view(run)


@router.post("/{run_id}/cancel", response_model=EvalRunView)
def cancel_eval_run(
    run_id: str,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> EvalRunView:
    run = db.scalar(
        select(EvalRunRecord).where(
            EvalRunRecord.id == run_id,
            EvalRunRecord.workspace_id == principal.workspace_id,
        )
    )
    if not run:
        raise HTTPException(status_code=404, detail="Eval run not found")
    if run.status not in {"CREATED", "QUEUED", "RUNNING"}:
        raise HTTPException(status_code=409, detail="Only active eval runs can be cancelled")
    run.status = "CANCELLED"
    db.add(
        AuditEvent(
            workspace_id=principal.workspace_id,
            actor_user_id=principal.user_id,
            event_type="eval_run.cancelled",
            entity_type="eval_run",
            entity_id=run.id,
            event_data={},
        )
    )
    db.commit()
    db.refresh(run)
    return run_view(run)


@router.get("/{run_id}/results", response_model=list[dict[str, Any]])
def list_eval_results(
    run_id: str,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    run = db.scalar(
        select(EvalRunRecord).where(
            EvalRunRecord.id == run_id, EvalRunRecord.workspace_id == principal.workspace_id
        )
    )
    if not run:
        raise HTTPException(status_code=404, detail="Eval run not found")
    results = db.scalars(
        select(EvalResultRecord)
        .where(
            EvalResultRecord.run_id == run_id,
            EvalResultRecord.workspace_id == principal.workspace_id,
        )
        .order_by(EvalResultRecord.created_at)
    ).all()
    return [
        {
            "id": result.id,
            "conversation_id": result.conversation_id,
            "evaluator_id": result.evaluator_id,
            "evaluator_version": result.evaluator_version,
            "verdict": result.verdict,
            "confidence": result.confidence,
            "severity": result.severity,
            "failure_code": result.failure_code,
            "reason": result.reason,
            "evidence": result.evidence,
            "judge_provenance": result.judge_provenance,
            "usage": result.usage,
        }
        for result in results
    ]
