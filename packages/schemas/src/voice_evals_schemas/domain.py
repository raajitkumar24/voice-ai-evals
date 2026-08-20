from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SchemaModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Speaker(StrEnum):
    CUSTOMER = "CUSTOMER"
    AGENT = "AGENT"
    HUMAN_AGENT = "HUMAN_AGENT"
    SYSTEM = "SYSTEM"
    UNKNOWN = "UNKNOWN"


class Verdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNCERTAIN = "UNCERTAIN"


class Severity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RootCauseOwner(StrEnum):
    PROMPT = "PROMPT"
    KNOWLEDGE_CONTENT = "KNOWLEDGE_CONTENT"
    RETRIEVAL = "RETRIEVAL"
    TOOL_SELECTION = "TOOL_SELECTION"
    TOOL_TIMING = "TOOL_TIMING"
    TOOL_ARGUMENTS = "TOOL_ARGUMENTS"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    TOOL_RESULT_USAGE = "TOOL_RESULT_USAGE"
    MODEL = "MODEL"
    LLM_CONFIGURATION = "LLM_CONFIGURATION"
    CONVERSATION_POLICY = "CONVERSATION_POLICY"
    DATA = "DATA"
    TRANSCRIPTION_OR_LANGUAGE = "TRANSCRIPTION_OR_LANGUAGE"
    UNKNOWN = "UNKNOWN"


class ToolStatus(StrEnum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class EvalRunStatus(StrEnum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RecommendationStatus(StrEnum):
    GENERATED = "GENERATED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISMISSED = "DISMISSED"


class ReviewAction(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    EDIT_AND_APPROVE = "EDIT_AND_APPROVE"
    MARK_NOT_ISSUE = "MARK_NOT_ISSUE"
    REQUEST_MORE_REVIEW = "REQUEST_MORE_REVIEW"


class ChangeType(StrEnum):
    PROMPT_PATCH = "PROMPT_PATCH"
    KB_GAP = "KB_GAP"
    KB_CONTENT_PATCH = "KB_CONTENT_PATCH"
    RETRIEVAL_CONFIG_CHANGE = "RETRIEVAL_CONFIG_CHANGE"
    TOOL_DESCRIPTION_PATCH = "TOOL_DESCRIPTION_PATCH"
    TOOL_SCHEMA_PATCH = "TOOL_SCHEMA_PATCH"
    TOOL_POLICY_PATCH = "TOOL_POLICY_PATCH"
    LLM_CONFIG_CHANGE = "LLM_CONFIG_CHANGE"
    DATA_QUALITY_FIX = "DATA_QUALITY_FIX"
    HUMAN_INVESTIGATION = "HUMAN_INVESTIGATION"


class LanguageMetadata(SchemaModel):
    code: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    code_switched: bool = False


class Translation(SchemaModel):
    language: str
    text: str
    generated_by: str | None = None


class Turn(SchemaModel):
    turn_id: str
    sequence: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)
    speaker: Speaker
    text_original: str
    language: LanguageMetadata | None = None
    translation: Translation | None = None


class RetrievedChunk(SchemaModel):
    chunk_id: str
    source_id: str
    content: str
    rank: int = Field(ge=1)
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrieverMetadata(SchemaModel):
    type: str
    top_k: int | None = Field(default=None, ge=1)
    threshold: float | None = None


class RetrievalEvent(SchemaModel):
    retrieval_event_id: str
    timestamp_ms: int = Field(ge=0)
    trigger_turn_id: str
    query_original: str
    query_rewritten: str | None = None
    retriever: RetrieverMetadata
    chunks: list[RetrievedChunk] = Field(default_factory=list)


class ArgumentSource(SchemaModel):
    source: str
    turn_id: str | None = None
    evidence_id: str | None = None


class ToolCall(SchemaModel):
    tool_call_id: str
    tool_definition_version_id: str
    trigger_turn_id: str
    timestamp_ms: int = Field(ge=0)
    arguments: dict[str, Any] = Field(default_factory=dict)
    argument_provenance: dict[str, ArgumentSource] = Field(default_factory=dict)
    status: ToolStatus
    result: Any = None
    duration_ms: int | None = Field(default=None, ge=0)


class LanguageSummary(SchemaModel):
    primary_language: str | None = None
    languages: list[str] = Field(default_factory=list)
    code_switching: bool = False


class ConversationOutcome(SchemaModel):
    goal_achieved: bool | None = None
    disposition: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationTrace(SchemaModel):
    schema_version: Literal["1.0"] = "1.0"
    conversation_id: str
    agent_id: str
    agent_config_version_id: str
    started_at: datetime
    ended_at: datetime | None = None
    channel: str = "voice"
    metadata: dict[str, Any] = Field(default_factory=dict)
    language_summary: LanguageSummary = Field(default_factory=LanguageSummary)
    turns: list[Turn] = Field(default_factory=list)
    retrieval_events: list[RetrievalEvent] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    outcome: ConversationOutcome | None = None

    @field_validator("turns")
    @classmethod
    def unique_turns_and_sequence(cls, turns: list[Turn]) -> list[Turn]:
        ids = [turn.turn_id for turn in turns]
        sequences = [turn.sequence for turn in turns]
        if len(ids) != len(set(ids)) or len(sequences) != len(set(sequences)):
            raise ValueError("turn IDs and sequence numbers must be unique")
        return turns


class ModelConfiguration(SchemaModel):
    provider: str
    model: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class AgentConfigurationVersion(SchemaModel):
    id: str
    agent_id: str
    version: str
    prompt: str
    model: ModelConfiguration
    tool_definition_version_ids: list[str] = Field(default_factory=list)
    knowledge_source_version_ids: list[str] = Field(default_factory=list)
    retrieval_config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class ToolDefinitionVersion(SchemaModel):
    id: str
    version: str
    name: str
    description: str
    input_schema: dict[str, Any]
    policy: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSourceType(StrEnum):
    TEXT = "TEXT"
    MARKDOWN = "MARKDOWN"
    PDF = "PDF"
    DOCX = "DOCX"
    URL_SNAPSHOT = "URL_SNAPSHOT"
    FAQ_JSON = "FAQ_JSON"


class IntegrationMaturity(StrEnum):
    LEVEL_1 = "LEVEL_1_TRANSCRIPT"
    LEVEL_2 = "LEVEL_2_GROUNDED_RAG"
    LEVEL_3 = "LEVEL_3_FULL_AGENT_TRACE"


class EvidenceReference(SchemaModel):
    type: Literal["TURN", "TOOL_CALL", "RETRIEVAL_EVENT", "CHUNK", "PROMPT", "KNOWLEDGE"]
    id: str
    detail: str | None = None


class JudgeProvenance(SchemaModel):
    provider: str
    model: str
    routing_profile_version: str
    requested_provider: str | None = None
    requested_model: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    retry_count: int = Field(default=0, ge=0)


class Usage(SchemaModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)


class EvalResult(SchemaModel):
    id: str
    eval_run_id: str
    conversation_id: str
    turn_id: str | None = None
    evaluator_id: str
    evaluator_version: str
    rubric_version: str | None = None
    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    severity: Severity
    failure_code: str | None = None
    reason: str
    evidence: list[EvidenceReference] = Field(default_factory=list)
    judge_provenance: JudgeProvenance
    usage: Usage = Field(default_factory=Usage)
    created_at: datetime
