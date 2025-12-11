"""Initial schema for AI Memory Layer."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision = "20240617_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    
    # Only create extension for PostgreSQL
    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Use appropriate UUID type based on database
    if is_postgres:
        id_column = sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True)
    else:
        # SQLite uses string for UUIDs
        id_column = sa.Column("id", sa.String(length=36), primary_key=True)
    
    op.create_table(
        "messages",
        id_column,
        sa.Column("tenant_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("conversation_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json") if is_postgres else sa.text("'{}'")),
        sa.Column("importance_score", sa.Float()),
        sa.Column("embedding", Vector(1536) if is_postgres else sa.Text()),  # SQLite doesn't support Vector type
        sa.Column(
            "embedding_status",
            sa.Enum("pending", "completed", "failed", name="embedding_status") if is_postgres else sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # Use appropriate UUID type for archived_messages
    if is_postgres:
        archived_id_column = sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True)
    else:
        archived_id_column = sa.Column("id", sa.String(length=36), primary_key=True)
    
    op.create_table(
        "archived_messages",
        archived_id_column,
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("conversation_id", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json") if is_postgres else sa.text("'{}'")),
        sa.Column("importance_score", sa.Float()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archive_reason", sa.String(length=255), nullable=False),
    )

    op.create_table(
        "retention_policies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("max_age_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("importance_threshold", sa.Float(), nullable=False),
        sa.Column("max_items", sa.Integer()),
        sa.Column("delete_after_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Use appropriate UUID type for embedding_jobs
    if is_postgres:
        job_id_column = sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True)
        job_message_id_column = sa.Column("message_id", sa.Uuid(as_uuid=True), nullable=False)
        job_status_column = sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", name="embedding_job_status"),
            nullable=False,
            server_default="pending",
        )
    else:
        job_id_column = sa.Column("id", sa.String(length=36), primary_key=True)
        job_message_id_column = sa.Column("message_id", sa.String(length=36), nullable=False)
        job_status_column = sa.Column(
            "status",
            sa.String(length=16),  # SQLite doesn't support ENUM
            nullable=False,
            server_default="pending",
        )
    
    op.create_table(
        "embedding_jobs",
        job_id_column,
        job_message_id_column,
        job_status_column,
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    
    # Only create foreign key for PostgreSQL (SQLite doesn't support ALTER for constraints)
    if is_postgres:
        op.create_foreign_key(
            "fk_embedding_jobs_message_id",
            "embedding_jobs",
            "messages",
            ["message_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    op.drop_constraint("fk_embedding_jobs_message_id", "embedding_jobs", type_="foreignkey")
    op.drop_table("embedding_jobs")
    op.drop_table("retention_policies")
    op.drop_table("archived_messages")
    op.drop_table("messages")
    sa.Enum(name="embedding_status").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="embedding_job_status").drop(op.get_bind(), checkfirst=False)
