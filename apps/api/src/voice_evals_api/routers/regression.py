from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    CandidatePatchRecord,
    Conversation,
    EvalResultRecord,
    EvalRunRecord,
    RegressionRunRecord,
)
from ..security import Principal, require_user

router = APIRouter(tags=["regression"])


class CandidatePatchCreate(BaseModel):
    recommendation_id: str | None = None
    change_type: str = Field(min_length=1, max_length=50)
    target: dict[str, Any] = Field(default_factory=dict)
    patch: dict[str, Any]


class RegressionRunCreate(BaseModel):
    candidate_patch_id: str
    baseline_eval_run_id: str
    candidate_eval_run_id: str


def _run(db: Session, workspace_id: str, run_id: str) -> EvalRunRecord:
    run = db.scalar(
        select(EvalRunRecord).where(
            EvalRunRecord.id == run_id,
            EvalRunRecord.workspace_id == workspace_id,
        )
    )
    if not run:
        raise HTTPException(status_code=404, detail=f"Eval run {run_id} not found")
    if run.status not in {"COMPLETED", "PARTIALLY_COMPLETED"}:
        raise HTTPException(status_code=409, detail=f"Eval run {run_id} is not complete")
    return run


def _result_map(
    db: Session, workspace_id: str, run_id: str
) -> dict[tuple[str, str], EvalResultRecord]:
    rows = db.execute(
        select(EvalResultRecord, Conversation)
        .join(Conversation, Conversation.id == EvalResultRecord.conversation_id)
        .where(
            EvalResultRecord.run_id == run_id,
            EvalResultRecord.workspace_id == workspace_id,
        )
    ).all()
    mapped: dict[tuple[str, str], EvalResultRecord] = {}
    for result, conversation in rows:
        case_id = conversation.trace_metadata.get("regression_case_id", conversation.external_id)
        key = (str(case_id), result.evaluator_id)
        if key in mapped:
            raise HTTPException(
                status_code=409,
                detail=f"Duplicate evaluator result for regression case {case_id}",
            )
        mapped[key] = result
    return mapped


def _pass_rate(results: list[EvalResultRecord]) -> float | None:
    evaluated = [item for item in results if item.verdict in {"PASS", "FAIL", "UNCERTAIN"}]
    if not evaluated:
        return None
    return round(sum(item.verdict == "PASS" for item in evaluated) / len(evaluated), 4)


@router.post("/candidate-patches", status_code=status.HTTP_201_CREATED)
def create_candidate_patch(
    payload: CandidatePatchCreate,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    candidate = CandidatePatchRecord(
        workspace_id=principal.workspace_id,
        recommendation_id=payload.recommendation_id,
        change_type=payload.change_type,
        target=payload.target,
        patch=payload.patch,
        created_by_user_id=principal.user_id,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return {
        "id": candidate.id,
        "status": candidate.status,
        "change_type": candidate.change_type,
        "target": candidate.target,
        "patch": candidate.patch,
    }


@router.post("/regression-runs", status_code=status.HTTP_201_CREATED)
def create_regression_run(
    payload: RegressionRunCreate,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    candidate_patch = db.scalar(
        select(CandidatePatchRecord).where(
            CandidatePatchRecord.id == payload.candidate_patch_id,
            CandidatePatchRecord.workspace_id == principal.workspace_id,
        )
    )
    if not candidate_patch:
        raise HTTPException(status_code=404, detail="Candidate patch not found")
    baseline_run = _run(db, principal.workspace_id, payload.baseline_eval_run_id)
    candidate_run = _run(db, principal.workspace_id, payload.candidate_eval_run_id)
    baseline_versions = set(baseline_run.snapshot.get("eval_definition_versions", []))
    candidate_versions = set(candidate_run.snapshot.get("eval_definition_versions", []))
    if baseline_versions != candidate_versions:
        raise HTTPException(
            status_code=409,
            detail="Baseline and candidate runs must use identical evaluator versions",
        )
    baseline = _result_map(db, principal.workspace_id, baseline_run.id)
    candidate = _result_map(db, principal.workspace_id, candidate_run.id)
    if set(baseline) != set(candidate):
        raise HTTPException(
            status_code=409,
            detail="Baseline and candidate runs must contain the same regression cases",
        )
    comparisons: list[dict[str, Any]] = []
    summary = {
        "fixed": 0,
        "unchanged_failures": 0,
        "new_regressions": 0,
        "critical_regressions": 0,
        "unchanged_passes": 0,
    }
    by_evaluator: dict[str, dict[str, list[EvalResultRecord]]] = defaultdict(
        lambda: {"baseline": [], "candidate": []}
    )
    for (case_id, evaluator_id), baseline_result in sorted(baseline.items()):
        candidate_result = candidate[(case_id, evaluator_id)]
        if baseline_result.verdict == "FAIL" and candidate_result.verdict == "PASS":
            outcome = "FIXED"
            summary["fixed"] += 1
        elif baseline_result.verdict == "FAIL" and candidate_result.verdict == "FAIL":
            outcome = "UNCHANGED_FAILURE"
            summary["unchanged_failures"] += 1
        elif baseline_result.verdict == "PASS" and candidate_result.verdict == "FAIL":
            outcome = "NEW_REGRESSION"
            summary["new_regressions"] += 1
            if candidate_result.severity == "CRITICAL":
                summary["critical_regressions"] += 1
        else:
            outcome = "UNCHANGED_OR_INCONCLUSIVE"
            if baseline_result.verdict == candidate_result.verdict == "PASS":
                summary["unchanged_passes"] += 1
        comparisons.append(
            {
                "case_id": case_id,
                "evaluator_id": evaluator_id,
                "baseline_result_id": baseline_result.id,
                "candidate_result_id": candidate_result.id,
                "baseline_verdict": baseline_result.verdict,
                "candidate_verdict": candidate_result.verdict,
                "candidate_severity": candidate_result.severity,
                "outcome": outcome,
            }
        )
        by_evaluator[evaluator_id]["baseline"].append(baseline_result)
        by_evaluator[evaluator_id]["candidate"].append(candidate_result)
    metric_deltas: dict[str, Any] = {}
    for evaluator_id, pair in by_evaluator.items():
        baseline_rate = _pass_rate(pair["baseline"])
        candidate_rate = _pass_rate(pair["candidate"])
        metric_deltas[evaluator_id] = {
            "baseline_pass_rate": baseline_rate,
            "candidate_pass_rate": candidate_rate,
            "delta": (
                round(candidate_rate - baseline_rate, 4)
                if baseline_rate is not None and candidate_rate is not None
                else None
            ),
        }
    safe_to_export = summary["new_regressions"] == 0 and summary["critical_regressions"] == 0
    regression = RegressionRunRecord(
        workspace_id=principal.workspace_id,
        candidate_patch_id=candidate_patch.id,
        baseline_eval_run_id=baseline_run.id,
        candidate_eval_run_id=candidate_run.id,
        status="COMPLETED",
        summary=summary,
        metric_deltas=metric_deltas,
        case_comparisons=comparisons,
        safe_to_export=safe_to_export,
    )
    db.add(regression)
    db.commit()
    db.refresh(regression)
    return {
        "id": regression.id,
        "status": regression.status,
        "summary": regression.summary,
        "metric_deltas": regression.metric_deltas,
        "case_comparisons": regression.case_comparisons,
        "safe_to_export": regression.safe_to_export,
    }


@router.get("/regression-runs/{regression_run_id}")
def get_regression_run(
    regression_run_id: str,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    regression = db.scalar(
        select(RegressionRunRecord).where(
            RegressionRunRecord.id == regression_run_id,
            RegressionRunRecord.workspace_id == principal.workspace_id,
        )
    )
    if not regression:
        raise HTTPException(status_code=404, detail="Regression run not found")
    return {
        "id": regression.id,
        "status": regression.status,
        "summary": regression.summary,
        "metric_deltas": regression.metric_deltas,
        "case_comparisons": regression.case_comparisons,
        "safe_to_export": regression.safe_to_export,
    }
