from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    AuditEvent,
    DraftPatchArtifact,
    FindingRecord,
    HumanReviewRecord,
    RecommendationRecord,
    RecommendationVersionRecord,
)
from ..security import Principal, require_user

router = APIRouter(tags=["findings and recommendations"])


class FindingView(BaseModel):
    id: str
    source_run_id: str | None
    signature: str
    title: str
    summary: str
    severity: str
    root_cause_owner: str
    confidence: float
    failure_codes: list[Any]
    result_ids: list[Any]
    affected_conversation_ids: list[Any]
    language_distribution: dict[str, Any]
    representative_evidence: list[Any]
    synthesis_provenance: dict[str, Any]
    status: str


class RecommendationView(BaseModel):
    id: str
    finding_id: str
    status: str
    change_type: str
    summary: str
    target: dict[str, Any]
    current_content: str | None
    proposed_content: str | None
    rationale: str
    confidence: float
    requires_business_fact_verification: bool
    synthesis_provenance: dict[str, Any]
    version: int


class ReviewCreate(BaseModel):
    action: Literal[
        "APPROVE",
        "REJECT",
        "EDIT_AND_APPROVE",
        "MARK_NOT_ISSUE",
        "REQUEST_MORE_REVIEW",
    ]
    comment: str | None = Field(default=None, max_length=5000)
    edited_proposal: dict[str, Any] | None = None


def finding_view(finding: FindingRecord) -> FindingView:
    return FindingView.model_validate(finding, from_attributes=True)


def recommendation_view(recommendation: RecommendationRecord) -> RecommendationView:
    return RecommendationView.model_validate(recommendation, from_attributes=True)


def _recommendation_or_404(
    db: Session, workspace_id: str, recommendation_id: str
) -> RecommendationRecord:
    recommendation = db.scalar(
        select(RecommendationRecord).where(
            RecommendationRecord.id == recommendation_id,
            RecommendationRecord.workspace_id == workspace_id,
        )
    )
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return recommendation


@router.get("/findings", response_model=list[FindingView])
def list_findings(
    run_id: str | None = None,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[FindingView]:
    query = select(FindingRecord).where(FindingRecord.workspace_id == principal.workspace_id)
    if run_id:
        query = query.where(FindingRecord.source_run_id == run_id)
    findings = db.scalars(query.order_by(FindingRecord.created_at.desc()).limit(500)).all()
    return [finding_view(item) for item in findings]


@router.get("/findings/{finding_id}", response_model=FindingView)
def get_finding(
    finding_id: str,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> FindingView:
    finding = db.scalar(
        select(FindingRecord).where(
            FindingRecord.id == finding_id,
            FindingRecord.workspace_id == principal.workspace_id,
        )
    )
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding_view(finding)


@router.get("/recommendations", response_model=list[RecommendationView])
def list_recommendations(
    finding_id: str | None = None,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[RecommendationView]:
    query = select(RecommendationRecord).where(
        RecommendationRecord.workspace_id == principal.workspace_id
    )
    if finding_id:
        query = query.where(RecommendationRecord.finding_id == finding_id)
    recommendations = db.scalars(
        query.order_by(RecommendationRecord.created_at.desc()).limit(500)
    ).all()
    return [recommendation_view(item) for item in recommendations]


@router.get("/recommendations/{recommendation_id}", response_model=RecommendationView)
def get_recommendation(
    recommendation_id: str,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> RecommendationView:
    return recommendation_view(
        _recommendation_or_404(db, principal.workspace_id, recommendation_id)
    )


@router.post(
    "/recommendations/{recommendation_id}/reviews",
    response_model=RecommendationView,
)
def review_recommendation(
    recommendation_id: str,
    payload: ReviewCreate,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> RecommendationView:
    recommendation = _recommendation_or_404(db, principal.workspace_id, recommendation_id)
    if recommendation.status in {"APPROVED", "REJECTED", "EDITED"}:
        raise HTTPException(status_code=409, detail="Recommendation review is already final")
    source_version = recommendation.version
    if payload.action == "EDIT_AND_APPROVE":
        if not payload.edited_proposal:
            raise HTTPException(status_code=422, detail="edited_proposal is required")
        allowed = {
            "change_type",
            "summary",
            "target",
            "current_content",
            "proposed_content",
            "rationale",
            "confidence",
        }
        unknown = set(payload.edited_proposal) - allowed
        if unknown:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported edited fields: {', '.join(sorted(unknown))}",
            )
        for field, value in payload.edited_proposal.items():
            setattr(recommendation, field, value)
        recommendation.version += 1
        recommendation.status = "EDITED"
        db.add(
            RecommendationVersionRecord(
                workspace_id=recommendation.workspace_id,
                recommendation_id=recommendation.id,
                version=recommendation.version,
                change_type=recommendation.change_type,
                summary=recommendation.summary,
                target=recommendation.target,
                current_content=recommendation.current_content,
                proposed_content=recommendation.proposed_content,
                rationale=recommendation.rationale,
                confidence=recommendation.confidence,
                created_by_user_id=principal.user_id,
            )
        )
    elif payload.action == "APPROVE":
        recommendation.status = "APPROVED"
    elif payload.action in {"REJECT", "MARK_NOT_ISSUE"}:
        recommendation.status = "REJECTED"
    else:
        recommendation.status = "PENDING_REVIEW"
    db.add(
        HumanReviewRecord(
            workspace_id=recommendation.workspace_id,
            recommendation_id=recommendation.id,
            reviewer_user_id=principal.user_id,
            action=payload.action,
            source_recommendation_version=source_version,
            edited_proposal=payload.edited_proposal,
            comment=payload.comment,
        )
    )
    db.add(
        AuditEvent(
            workspace_id=recommendation.workspace_id,
            actor_user_id=principal.user_id,
            event_type="RECOMMENDATION_REVIEWED",
            entity_type="recommendation",
            entity_id=recommendation.id,
            event_data={
                "action": payload.action,
                "source_version": source_version,
                "resulting_version": recommendation.version,
                "status": recommendation.status,
            },
        )
    )
    db.commit()
    db.refresh(recommendation)
    return recommendation_view(recommendation)


@router.post(
    "/recommendations/{recommendation_id}/draft-artifacts",
    status_code=status.HTTP_201_CREATED,
)
def create_draft_artifact(
    recommendation_id: str,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    recommendation = _recommendation_or_404(db, principal.workspace_id, recommendation_id)
    if recommendation.status not in {"APPROVED", "EDITED"}:
        raise HTTPException(
            status_code=409,
            detail="Human approval is required before creating a draft artifact",
        )
    content = {
        "schema_version": "1.0",
        "draft_only": True,
        "production_writeback_supported": False,
        "recommendation_id": recommendation.id,
        "recommendation_version": recommendation.version,
        "change_type": recommendation.change_type,
        "target": recommendation.target,
        "current_content": recommendation.current_content,
        "proposed_content": recommendation.proposed_content,
        "rationale": recommendation.rationale,
    }
    artifact = DraftPatchArtifact(
        workspace_id=recommendation.workspace_id,
        recommendation_id=recommendation.id,
        recommendation_version=recommendation.version,
        format="JSON",
        content=content,
        created_by_user_id=principal.user_id,
    )
    db.add(artifact)
    db.add(
        AuditEvent(
            workspace_id=recommendation.workspace_id,
            actor_user_id=principal.user_id,
            event_type="DRAFT_PATCH_EXPORTED",
            entity_type="recommendation",
            entity_id=recommendation.id,
            event_data={"recommendation_version": recommendation.version},
        )
    )
    db.commit()
    db.refresh(artifact)
    return {"id": artifact.id, "format": artifact.format, "content": artifact.content}
