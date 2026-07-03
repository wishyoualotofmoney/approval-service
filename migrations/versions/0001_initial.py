"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reviewer_user_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("decision_comment", sa.Text(), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("decided_by", sa.String(length=128), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_approval_requests_workspace_id",
        "approval_requests",
        ["workspace_id"],
    )
    op.create_index(
        "ix_approval_requests_status", "approval_requests", ["status"]
    )

    op.create_table(
        "approval_audit_log",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("actor_user_id", sa.String(length=128), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_approval_audit_log_workspace_id",
        "approval_audit_log",
        ["workspace_id"],
    )
    op.create_index(
        "ix_approval_audit_log_request_id",
        "approval_audit_log",
        ["request_id"],
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_outbox_events_workspace_id", "outbox_events", ["workspace_id"]
    )
    op.create_index(
        "ix_outbox_events_aggregate_id", "outbox_events", ["aggregate_id"]
    )

    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("endpoint", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "key", name="uq_idempotency_ws_key"),
    )


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_index("ix_outbox_events_aggregate_id", table_name="outbox_events")
    op.drop_index("ix_outbox_events_workspace_id", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index(
        "ix_approval_audit_log_request_id", table_name="approval_audit_log"
    )
    op.drop_index(
        "ix_approval_audit_log_workspace_id", table_name="approval_audit_log"
    )
    op.drop_table("approval_audit_log")
    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_index(
        "ix_approval_requests_workspace_id", table_name="approval_requests"
    )
    op.drop_table("approval_requests")
