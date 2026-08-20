from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Conversation, Dataset
from ..security import Principal, require_user

router = APIRouter(prefix="/datasets", tags=["datasets"])


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    conversation_ids: list[str] = Field(default_factory=list, max_length=10_000)


def _view(dataset: Dataset) -> dict[str, Any]:
    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "conversation_ids": dataset.conversation_ids,
        "version": dataset.version,
        "created_at": dataset.created_at,
    }


def _resolve_conversations(
    db: Session, workspace_id: str, identities: list[str]
) -> list[Conversation]:
    if not identities:
        return []
    conversations = db.scalars(
        select(Conversation).where(
            Conversation.workspace_id == workspace_id,
            Conversation.deleted_at.is_(None),
            (Conversation.id.in_(identities)) | (Conversation.external_id.in_(identities)),
        )
    ).all()
    if len(conversations) != len(set(identities)):
        raise HTTPException(status_code=404, detail="One or more conversations were not found")
    return list(conversations)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_dataset(
    payload: DatasetCreate,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    conversations = _resolve_conversations(db, principal.workspace_id, payload.conversation_ids)
    current_version = db.scalar(
        select(func.max(Dataset.version)).where(
            Dataset.workspace_id == principal.workspace_id, Dataset.name == payload.name
        )
    )
    dataset = Dataset(
        workspace_id=principal.workspace_id,
        name=payload.name,
        description=payload.description,
        conversation_ids=[item.id for item in conversations],
        version=(current_version or 0) + 1,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return _view(dataset)


@router.get("")
def list_datasets(
    principal: Principal = Depends(require_user), db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    records = db.scalars(
        select(Dataset)
        .where(Dataset.workspace_id == principal.workspace_id)
        .order_by(Dataset.created_at.desc())
        .limit(500)
    ).all()
    return [_view(item) for item in records]


@router.get("/{dataset_id}")
def get_dataset(
    dataset_id: str,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    dataset = db.scalar(
        select(Dataset).where(
            Dataset.id == dataset_id, Dataset.workspace_id == principal.workspace_id
        )
    )
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return _view(dataset)


@router.post("/{dataset_id}/conversations/{conversation_id}", status_code=status.HTTP_201_CREATED)
def add_conversation_version(
    dataset_id: str,
    conversation_id: str,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    source = db.scalar(
        select(Dataset).where(
            Dataset.id == dataset_id, Dataset.workspace_id == principal.workspace_id
        )
    )
    if not source:
        raise HTTPException(status_code=404, detail="Dataset not found")
    conversation = _resolve_conversations(db, principal.workspace_id, [conversation_id])[0]
    conversation_ids = list(dict.fromkeys([*source.conversation_ids, conversation.id]))
    latest_version = db.scalar(
        select(func.max(Dataset.version)).where(
            Dataset.workspace_id == principal.workspace_id, Dataset.name == source.name
        )
    )
    version = Dataset(
        workspace_id=principal.workspace_id,
        name=source.name,
        description=source.description,
        conversation_ids=conversation_ids,
        version=(latest_version or source.version) + 1,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return _view(version)
