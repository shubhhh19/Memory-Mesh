"""Allow embedding column to accept any configured dimension."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20241129_01"
down_revision = "20240620_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(sa.text("ALTER TABLE messages ALTER COLUMN embedding TYPE vector"))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    # Default back to 1536 dimensions which was the previous schema.
    op.execute(sa.text("ALTER TABLE messages ALTER COLUMN embedding TYPE vector(1536)"))

