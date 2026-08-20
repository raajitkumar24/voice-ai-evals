from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def new_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )


class Workspace(TimestampMixin, Base):
    __tablename__ = "workspaces"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class WorkspaceMembership(TimestampMixin, Base):
    __tablename__ = "workspace_memberships"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(30), default="OWNER")


class AuthSession(TimestampMixin, Base):
    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class WorkspaceApiKey(TimestampMixin, Base):
    __tablename__ = "workspace_api_keys"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    prefix: Mapped[str] = mapped_column(String(16), index=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProviderConnection(TimestampMixin, Base):
    __tablename__ = "provider_connections"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    provider: Mapped[str] = mapped_column(String(50))
    base_url: Mapped[str | None] = mapped_column(Text)
    default_model: Mapped[str | None] = mapped_column(String(200))
    secret_ciphertext: Mapped[str | None] = mapped_column(Text)
    secret_source: Mapped[str] = mapped_column(String(30), default="ENCRYPTED_DB")
    capability_overrides: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="UNTESTED")
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Agent(TimestampMixin, Base):
    __tablename__ = "agents"
    __table_args__ = (UniqueConstraint("workspace_id", "external_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)


class AgentConfigurationVersion(TimestampMixin, Base):
    __tablename__ = "agent_configuration_versions"
    __table_args__ = (
        UniqueConstraint("workspace_id", "external_id", name="uq_agent_config_workspace_external"),
        UniqueConstraint("workspace_id", "agent_id", "version"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(100))
    prompt: Mapped[str] = mapped_column(Text)
    model_config_data: Mapped[dict[str, Any]] = mapped_column("model_config", JSON, default=dict)
    tool_definition_version_ids: Mapped[list[Any]] = mapped_column(JSON, default=list)
    knowledge_source_version_ids: Mapped[list[Any]] = mapped_column(JSON, default=list)
    retrieval_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class KnowledgeSourceVersion(TimestampMixin, Base):
    __tablename__ = "knowledge_source_versions"
    __table_args__ = (UniqueConstraint("workspace_id", "external_id", "version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(100))
    source_type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(300))
    content_hash: Mapped[str] = mapped_column(String(64))
    storage_uri: Mapped[str | None] = mapped_column(Text)
    parsed_text: Mapped[str | None] = mapped_column(Text)
    source_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class ToolDefinitionVersion(TimestampMixin, Base):
    __tablename__ = "tool_definition_versions"
    __table_args__ = (UniqueConstraint("workspace_id", "external_id", "version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("workspace_id", "external_id"),
        Index("ix_conversations_workspace_started", "workspace_id", "started_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(200))
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="RESTRICT"), index=True)
    agent_config_version_id: Mapped[str] = mapped_column(
        ForeignKey("agent_configuration_versions.id", ondelete="RESTRICT")
    )
    schema_version: Mapped[str] = mapped_column(String(20), default="1.0")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    channel: Mapped[str] = mapped_column(String(30), default="voice")
    trace_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    language_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    outcome: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    source_hash: Mapped[str] = mapped_column(String(64))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    turns: Mapped[list[TurnRecord]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="TurnRecord.sequence"
    )


class RawIngestionEnvelope(TimestampMixin, Base):
    __tablename__ = "raw_ingestion_envelopes"
    __table_args__ = (UniqueConstraint("workspace_id", "endpoint", "idempotency_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    endpoint: Mapped[str] = mapped_column(String(100))
    idempotency_key: Mapped[str] = mapped_column(String(200))
    payload_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="RECEIVED")
    canonical_entity_id: Mapped[str | None] = mapped_column(String(36))
    error: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class TurnRecord(TimestampMixin, Base):
    __tablename__ = "turns"
    __table_args__ = (
        UniqueConstraint("conversation_id", "external_id"),
        UniqueConstraint("conversation_id", "sequence"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(200))
    sequence: Mapped[int] = mapped_column(Integer)
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    speaker: Mapped[str] = mapped_column(String(30))
    text_original: Mapped[str] = mapped_column(Text)
    language: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    translation: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    conversation: Mapped[Conversation] = relationship(back_populates="turns")


class RetrievalEventRecord(TimestampMixin, Base):
    __tablename__ = "retrieval_events"
    __table_args__ = (UniqueConstraint("conversation_id", "external_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(200))
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    trigger_turn_id: Mapped[str] = mapped_column(String(200))
    query_original: Mapped[str] = mapped_column(Text)
    query_rewritten: Mapped[str | None] = mapped_column(Text)
    retriever: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    chunks: Mapped[list[Any]] = mapped_column(JSON, default=list)


class ToolCallRecord(TimestampMixin, Base):
    __tablename__ = "tool_calls"
    __table_args__ = (UniqueConstraint("conversation_id", "external_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(200))
    tool_definition_version_id: Mapped[str] = mapped_column(String(200))
    trigger_turn_id: Mapped[str] = mapped_column(String(200))
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    argument_provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30))
    result: Mapped[dict[str, Any] | list[Any] | str | int | float | bool | None] = mapped_column(
        JSON
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class Dataset(TimestampMixin, Base):
    __tablename__ = "datasets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    conversation_ids: Mapped[list[Any]] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)


class EvalDefinitionRecord(TimestampMixin, Base):
    __tablename__ = "eval_definitions"
    __table_args__ = (UniqueConstraint("workspace_id", "definition_id", "version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    definition_id: Mapped[str] = mapped_column(String(150))
    version: Mapped[str] = mapped_column(String(50))
    family: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200))
    config: Mapped[dict[str, Any]] = mapped_column(JSON)


class EvalSuiteRecord(TimestampMixin, Base):
    __tablename__ = "eval_suites"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(50))
    definition_versions: Mapped[list[Any]] = mapped_column(JSON, default=list)
    thresholds: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class EvalRunRecord(TimestampMixin, Base):
    __tablename__ = "eval_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    dataset_id: Mapped[str | None] = mapped_column(ForeignKey("datasets.id", ondelete="SET NULL"))
    suite_id: Mapped[str | None] = mapped_column(ForeignKey("eval_suites.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(40), default="CREATED", index=True)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    sampling_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    routing_profile: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    counts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    warnings: Mapped[list[Any]] = mapped_column(JSON, default=list)
    errors: Mapped[list[Any]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EvalResultRecord(TimestampMixin, Base):
    __tablename__ = "eval_results"
    __table_args__ = (
        UniqueConstraint(
            "run_id", "conversation_id", "turn_id", "evaluator_id", "evaluator_version"
        ),
        Index("ix_eval_results_workspace_verdict", "workspace_id", "verdict"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    run_id: Mapped[str] = mapped_column(ForeignKey("eval_runs.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    turn_id: Mapped[str | None] = mapped_column(String(200))
    evaluator_id: Mapped[str] = mapped_column(String(150))
    evaluator_version: Mapped[str] = mapped_column(String(50))
    rubric_version: Mapped[str | None] = mapped_column(String(50))
    verdict: Mapped[str] = mapped_column(String(30))
    confidence: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(30))
    failure_code: Mapped[str | None] = mapped_column(String(150))
    reason: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list[Any]] = mapped_column(JSON, default=list)
    judge_provenance: Mapped[dict[str, Any]] = mapped_column(JSON)
    usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class FindingRecord(TimestampMixin, Base):
    __tablename__ = "findings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    source_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("eval_runs.id", ondelete="CASCADE"), index=True
    )
    signature: Mapped[str] = mapped_column(String(500), index=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(30))
    root_cause_owner: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(Float)
    failure_codes: Mapped[list[Any]] = mapped_column(JSON, default=list)
    result_ids: Mapped[list[Any]] = mapped_column(JSON, default=list)
    affected_conversation_ids: Mapped[list[Any]] = mapped_column(JSON, default=list)
    language_distribution: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    representative_evidence: Mapped[list[Any]] = mapped_column(JSON, default=list)
    synthesis_provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="OPEN")


class RecommendationRecord(TimestampMixin, Base):
    __tablename__ = "recommendations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    finding_id: Mapped[str] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(40), default="PENDING_REVIEW")
    change_type: Mapped[str] = mapped_column(String(50))
    summary: Mapped[str] = mapped_column(Text)
    target: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    current_content: Mapped[str | None] = mapped_column(Text)
    proposed_content: Mapped[str | None] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    requires_business_fact_verification: Mapped[bool] = mapped_column(Boolean, default=False)
    synthesis_provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    regression_run_id: Mapped[str | None] = mapped_column(String(36))


class RecommendationVersionRecord(Base):
    __tablename__ = "recommendation_versions"
    __table_args__ = (UniqueConstraint("recommendation_id", "version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    change_type: Mapped[str] = mapped_column(String(50))
    summary: Mapped[str] = mapped_column(Text)
    target: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    current_content: Mapped[str | None] = mapped_column(Text)
    proposed_content: Mapped[str | None] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class DraftPatchArtifact(TimestampMixin, Base):
    __tablename__ = "draft_patch_artifacts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), index=True
    )
    recommendation_version: Mapped[int] = mapped_column(Integer)
    format: Mapped[str] = mapped_column(String(30), default="JSON")
    content: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))


class CandidatePatchRecord(TimestampMixin, Base):
    __tablename__ = "candidate_patches"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    recommendation_id: Mapped[str | None] = mapped_column(
        ForeignKey("recommendations.id", ondelete="SET NULL"), index=True
    )
    change_type: Mapped[str] = mapped_column(String(50))
    target: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    patch: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))


class RegressionRunRecord(TimestampMixin, Base):
    __tablename__ = "regression_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    candidate_patch_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_patches.id", ondelete="CASCADE"), index=True
    )
    baseline_eval_run_id: Mapped[str] = mapped_column(
        ForeignKey("eval_runs.id", ondelete="RESTRICT"), index=True
    )
    candidate_eval_run_id: Mapped[str] = mapped_column(
        ForeignKey("eval_runs.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="COMPLETED")
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    metric_deltas: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    case_comparisons: Mapped[list[Any]] = mapped_column(JSON, default=list)
    safe_to_export: Mapped[bool] = mapped_column(Boolean, default=False)


class HumanReviewRecord(TimestampMixin, Base):
    __tablename__ = "human_reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), index=True
    )
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    action: Mapped[str] = mapped_column(String(50))
    source_recommendation_version: Mapped[int] = mapped_column(Integer)
    edited_proposal: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    comment: Mapped[str | None] = mapped_column(Text)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    actor_user_id: Mapped[str | None] = mapped_column(String(36))
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(100))
    event_data: Mapped[dict[str, Any]] = mapped_column("data", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, index=True
    )
