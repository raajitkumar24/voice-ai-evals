from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Conversation, EvalResultRecord, EvalRunRecord, FindingRecord
from ..security import Principal, require_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


@router.get("/overview")
def overview(
    run_id: str,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    run = db.scalar(
        select(EvalRunRecord).where(
            EvalRunRecord.id == run_id,
            EvalRunRecord.workspace_id == principal.workspace_id,
        )
    )
    if not run:
        raise HTTPException(status_code=404, detail="Eval run not found")
    rows = db.execute(
        select(
            EvalResultRecord.evaluator_id,
            EvalResultRecord.verdict,
            EvalResultRecord.severity,
            func.count(EvalResultRecord.id),
        )
        .where(
            EvalResultRecord.run_id == run.id,
            EvalResultRecord.workspace_id == principal.workspace_id,
        )
        .group_by(
            EvalResultRecord.evaluator_id,
            EvalResultRecord.verdict,
            EvalResultRecord.severity,
        )
    ).all()
    counts: dict[tuple[str, str, str], int] = {
        (evaluator, verdict, severity): count for evaluator, verdict, severity, count in rows
    }

    def family_rate(evaluator_id: str) -> float | None:
        passed = sum(
            count
            for (evaluator, verdict, _), count in counts.items()
            if evaluator == evaluator_id and verdict == "PASS"
        )
        evaluated = sum(
            count
            for (evaluator, verdict, _), count in counts.items()
            if evaluator == evaluator_id and verdict in {"PASS", "FAIL", "UNCERTAIN"}
        )
        return _rate(passed, evaluated)

    passed = sum(count for (_, verdict, _), count in counts.items() if verdict == "PASS")
    failed = sum(count for (_, verdict, _), count in counts.items() if verdict == "FAIL")
    uncertain = sum(count for (_, verdict, _), count in counts.items() if verdict == "UNCERTAIN")
    total = sum(counts.values())
    evaluated = passed + failed + uncertain
    critical_failures = sum(
        count
        for (_, verdict, severity), count in counts.items()
        if verdict == "FAIL" and severity == "CRITICAL"
    )
    owner_rows = db.execute(
        select(FindingRecord.root_cause_owner, func.count(FindingRecord.id))
        .where(
            FindingRecord.workspace_id == principal.workspace_id,
            FindingRecord.source_run_id == run.id,
        )
        .group_by(FindingRecord.root_cause_owner)
        .order_by(func.count(FindingRecord.id).desc())
    ).all()
    return {
        "run_id": run.id,
        "status": run.status,
        "metrics": {
            "eval_pass_rate": _rate(passed, evaluated),
            "critical_failure_rate": _rate(critical_failures, evaluated),
            "grounded_response_rate": family_rate("grounding"),
            "tool_execution_accuracy": family_rate("tool_trajectory"),
            "knowledge_coverage": family_rate("rag"),
            "conversation_quality": family_rate("conversation"),
            "eval_coverage": _rate(evaluated, total),
        },
        "denominators": {"total_results": total, "evaluated_results": evaluated},
        "counts": {
            "pass": passed,
            "fail": failed,
            "uncertain": uncertain,
            "not_applicable": total - evaluated,
            "critical_failures": critical_failures,
        },
        "failure_ownership": [{"owner": owner, "count": count} for owner, count in owner_rows],
        "usage": run.usage,
        "errors": run.errors,
    }


@router.get("/languages")
def language_performance(
    run_id: str,
    minimum_sample_size: int = 5,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    run_exists = db.scalar(
        select(func.count(EvalRunRecord.id)).where(
            EvalRunRecord.id == run_id,
            EvalRunRecord.workspace_id == principal.workspace_id,
        )
    )
    if not run_exists:
        raise HTTPException(status_code=404, detail="Eval run not found")
    language = func.coalesce(
        Conversation.language_summary["primary_language"].as_string(), "unknown"
    )
    rows = db.execute(
        select(
            language.label("language"),
            func.count(EvalResultRecord.id).label("total"),
            func.sum(case((EvalResultRecord.verdict == "PASS", 1), else_=0)).label("passed"),
            func.sum(
                case(
                    (EvalResultRecord.verdict.in_(["PASS", "FAIL", "UNCERTAIN"]), 1),
                    else_=0,
                )
            ).label("evaluated"),
        )
        .join(Conversation, Conversation.id == EvalResultRecord.conversation_id)
        .where(
            EvalResultRecord.run_id == run_id,
            EvalResultRecord.workspace_id == principal.workspace_id,
        )
        .group_by(language)
        .order_by(language)
    ).all()
    performance = [
        {
            "language": row.language,
            "total_results": row.total,
            "evaluated_results": row.evaluated,
            "pass_rate": _rate(row.passed, row.evaluated),
            "meets_minimum_sample": row.evaluated >= minimum_sample_size,
        }
        for row in rows
    ]
    eligible_rates = [
        item["pass_rate"]
        for item in performance
        if item["meets_minimum_sample"] and item["pass_rate"] is not None
    ]
    return {
        "run_id": run_id,
        "minimum_sample_size": minimum_sample_size,
        "performance": performance,
        "language_performance_gap": (
            round(max(eligible_rates) - min(eligible_rates), 4)
            if len(eligible_rates) >= 2
            else None
        ),
    }
