from sqlalchemy import select
from sqlalchemy.orm import Session
from voice_evals_eval_core import load_eval_definitions

from .config import Settings
from .models import EvalDefinitionRecord, EvalSuiteRecord, User, Workspace, WorkspaceMembership
from .security import hash_password


def bootstrap_local_workspace(db: Session, settings: Settings) -> None:
    if settings.is_production and settings.bootstrap_password == "change-me-before-production":
        raise RuntimeError("A non-default bootstrap password is required in production")
    workspace = db.scalar(select(Workspace).where(Workspace.slug == "default"))
    if not workspace:
        workspace = Workspace(name="Default Workspace", slug="default")
        db.add(workspace)
        db.flush()
    email = settings.bootstrap_email.lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        user = User(email=email, password_hash=hash_password(settings.bootstrap_password))
        db.add(user)
        db.flush()
    membership = db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace.id,
            WorkspaceMembership.user_id == user.id,
        )
    )
    if not membership:
        db.add(WorkspaceMembership(workspace_id=workspace.id, user_id=user.id, role="OWNER"))
    _seed_default_eval_suite(db, workspace.id)
    db.commit()


def _seed_default_eval_suite(db: Session, workspace_id: str) -> None:
    definitions = load_eval_definitions()
    identities: list[str] = []
    for definition in definitions:
        identities.append(f"{definition.id}:{definition.version}")
        existing = db.scalar(
            select(EvalDefinitionRecord).where(
                EvalDefinitionRecord.workspace_id == workspace_id,
                EvalDefinitionRecord.definition_id == definition.id,
                EvalDefinitionRecord.version == definition.version,
            )
        )
        if not existing:
            db.add(
                EvalDefinitionRecord(
                    workspace_id=workspace_id,
                    definition_id=definition.id,
                    version=definition.version,
                    family=definition.family,
                    name=definition.name,
                    config=definition.model_dump(mode="json"),
                )
            )
    suite = db.scalar(
        select(EvalSuiteRecord).where(
            EvalSuiteRecord.workspace_id == workspace_id,
            EvalSuiteRecord.name == "Default Voice Agent Suite",
            EvalSuiteRecord.version == "1",
        )
    )
    if not suite:
        db.add(
            EvalSuiteRecord(
                workspace_id=workspace_id,
                name="Default Voice Agent Suite",
                version="1",
                definition_versions=identities,
                thresholds={"critical_failure_rate_max": 0.01},
            )
        )
