"""Add performance indexes to messages table."""

from __future__ import annotations

from alembic import op

revision = "20240620_01"
down_revision = "20240617_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_messages_created_at", "messages", ["created_at"])
    op.create_index("ix_messages_archived", "messages", ["archived"])
    op.create_index("ix_messages_tenant_archived", "messages", ["tenant_id", "archived"])


def downgrade() -> None:
    op.drop_index("ix_messages_tenant_archived", table_name="messages")
    op.drop_index("ix_messages_archived", table_name="messages")
    op.drop_index("ix_messages_created_at", table_name="messages")
