from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from voice_evals_eval_core import EvalDefinition

from ..db import get_db
from ..models import EvalDefinitionRecord, EvalSuiteRecord
from ..security import Principal, require_user

router = APIRouter(prefix="/eval-setup", tags=["evaluation setup"])


class DefinitionCreate(BaseModel):
    definition: EvalDefinition


class SuiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=50)
    definition_versions: list[str] = Field(min_length=1)
    thresholds: dict[str, Any] = Field(default_factory=dict)


@router.get("/definitions")
def list_definitions(
    principal: Principal = Depends(require_user), db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    records = db.scalars(
        select(EvalDefinitionRecord)
        .where(EvalDefinitionRecord.workspace_id == principal.workspace_id)
        .order_by(EvalDefinitionRecord.family, EvalDefinitionRecord.name)
    ).all()
    return [record.config for record in records]


@router.post("/definitions", status_code=status.HTTP_201_CREATED)
def create_definition(
    payload: DefinitionCreate,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    definition = payload.definition
    existing = db.scalar(
        select(EvalDefinitionRecord).where(
            EvalDefinitionRecord.workspace_id == principal.workspace_id,
            EvalDefinitionRecord.definition_id == definition.id,
            EvalDefinitionRecord.version == definition.version,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Evaluator version already exists")
    record = EvalDefinitionRecord(
        workspace_id=principal.workspace_id,
        definition_id=definition.id,
        version=definition.version,
        family=definition.family,
        name=definition.name,
        config=definition.model_dump(mode="json"),
    )
    db.add(record)
    db.commit()
    return record.config


@router.get("/suites")
def list_suites(
    principal: Principal = Depends(require_user), db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    suites = db.scalars(
        select(EvalSuiteRecord)
        .where(EvalSuiteRecord.workspace_id == principal.workspace_id)
        .order_by(EvalSuiteRecord.created_at.desc())
    ).all()
    return [
        {
            "id": suite.id,
            "name": suite.name,
            "version": suite.version,
            "definition_versions": suite.definition_versions,
            "thresholds": suite.thresholds,
        }
        for suite in suites
    ]


@router.post("/suites", status_code=status.HTTP_201_CREATED)
def create_suite(
    payload: SuiteCreate,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    available = {
        f"{record.definition_id}:{record.version}"
        for record in db.scalars(
            select(EvalDefinitionRecord).where(
                EvalDefinitionRecord.workspace_id == principal.workspace_id
            )
        ).all()
    }
    missing = set(payload.definition_versions) - available
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown evaluator versions: {', '.join(sorted(missing))}",
        )
    existing = db.scalar(
        select(EvalSuiteRecord).where(
            EvalSuiteRecord.workspace_id == principal.workspace_id,
            EvalSuiteRecord.name == payload.name,
            EvalSuiteRecord.version == payload.version,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Eval suite version already exists")
    suite = EvalSuiteRecord(
        workspace_id=principal.workspace_id,
        name=payload.name,
        version=payload.version,
        definition_versions=payload.definition_versions,
        thresholds=payload.thresholds,
    )
    db.add(suite)
    db.commit()
    db.refresh(suite)
    return {
        "id": suite.id,
        "name": suite.name,
        "version": suite.version,
        "definition_versions": suite.definition_versions,
        "thresholds": suite.thresholds,
    }
