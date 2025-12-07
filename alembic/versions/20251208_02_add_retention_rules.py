"""Add retention rules table for advanced lifecycle management."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251208_02"
down_revision = "20251208_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    
    op.create_table(
        "retention_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "rule_type",
            sa.String(length=32),
            nullable=False,
            comment="age, importance, conversation_age, max_items, custom",
        ),
        sa.Column("conditions", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json") if is_postgres else "'{}'"),
        sa.Column(
            "action",
            sa.String(length=32),
            nullable=False,
            comment="archive, delete, move_to_cold_storage",
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true" if is_postgres else "1")),
        sa.Column("last_applied", sa.DateTime(timezone=True) if is_postgres else sa.DateTime()),
        sa.Column("created_at", sa.DateTime(timezone=True) if is_postgres else sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True) if is_postgres else sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("retention_rules", if_exists=True)

