from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import Field
from voice_evals_schemas import (
    AgentConfigurationVersion,
    ConversationTrace,
    EvidenceReference,
    SchemaModel,
    Severity,
    Verdict,
)


class JudgeOutput(SchemaModel):
    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    severity: Severity
    failure_code: str | None = None
    reason: str
    evidence: list[EvidenceReference] = Field(default_factory=list)


class EvalDefinition(SchemaModel):
    id: str
    version: str
    name: str
    family: str
    scope: str = "CONVERSATION"
    severity: Severity = Severity.MEDIUM
    description: str
    applicability: str
    prompt_template: str
    output_schema: str = "judge_output_v1"


class RootCauseOutput(SchemaModel):
    root_cause_owner: str
    primary_failure_code: str
    secondary_effects: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    ruled_out_causes: list[str] = Field(default_factory=list)
    remediation_class: str
    requires_human_investigation: bool = False


class RecommendationOutput(SchemaModel):
    change_type: str
    summary: str
    target: dict[str, Any] = Field(default_factory=dict)
    current_content: str | None = None
    proposed_content: str | None = None
    rationale: str
    confidence: float = Field(ge=0, le=1)
    requires_business_fact_verification: bool = False


@dataclass(frozen=True)
class EvaluationContext:
    trace: ConversationTrace
    agent_configuration: AgentConfigurationVersion
    knowledge_sources: list[dict[str, Any]] = field(default_factory=list)
    tool_definitions: list[dict[str, Any]] = field(default_factory=list)
