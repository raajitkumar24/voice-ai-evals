"""add ingestion lineage

Revision ID: 1fddbe4854ad
Revises: e7f4b5025037
Create Date: 2026-08-20 12:49:12.742828
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1fddbe4854ad"
down_revision: str | None = "e7f4b5025037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "raw_ingestion_envelopes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("endpoint", sa.String(length=100), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("canonical_entity_id", sa.String(length=36), nullable=True),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "endpoint", "idempotency_key"),
    )
    op.create_index(
        op.f("ix_raw_ingestion_envelopes_workspace_id"),
        "raw_ingestion_envelopes",
        ["workspace_id"],
        unique=False,
    )
    with op.batch_alter_table("agent_configuration_versions") as batch_op:
        batch_op.add_column(sa.Column("external_id", sa.String(length=200), nullable=True))
    op.execute("UPDATE agent_configuration_versions SET external_id = id")
    with op.batch_alter_table("agent_configuration_versions") as batch_op:
        batch_op.alter_column("external_id", nullable=False)
        batch_op.create_unique_constraint(
            "uq_agent_config_workspace_external", ["workspace_id", "external_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_configuration_versions") as batch_op:
        batch_op.drop_constraint("uq_agent_config_workspace_external", type_="unique")
        batch_op.drop_column("external_id")
    op.drop_index(
        op.f("ix_raw_ingestion_envelopes_workspace_id"),
        table_name="raw_ingestion_envelopes",
    )
    op.drop_table("raw_ingestion_envelopes")
