"""Add authentication and conversation management tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20251208_01"
down_revision = "20241129_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    is_sqlite = bind.dialect.name == "sqlite"
    
    # Create user_role enum (PostgreSQL only)
    if is_postgres:
        user_role_enum = sa.Enum("admin", "user", "read_only", name="userrole")
        user_role_enum.create(op.get_bind(), checkfirst=True)
        role_column = sa.Column("role", user_role_enum, nullable=False, server_default="user")
    else:
        # SQLite uses string
        role_column = sa.Column("role", sa.String(length=16), nullable=False, server_default="user")
    
    # Create users table
    if is_sqlite:
        # SQLite version - use string for UUIDs
        op.create_table(
            "users",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("email", sa.String(length=255), nullable=False, unique=True),
            sa.Column("username", sa.String(length=64), nullable=False, unique=True),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("full_name", sa.String(length=255)),
            sa.Column("role", sa.String(length=16), nullable=False, server_default="user"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("tenant_id", sa.String(length=64)),
            sa.Column("metadata", sa.Text(), server_default="'{}'"),
            sa.Column("last_login", sa.DateTime()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
    elif is_postgres:
        op.create_table(
            "users",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("email", sa.String(length=255), nullable=False, unique=True, index=True),
            sa.Column("username", sa.String(length=64), nullable=False, unique=True, index=True),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("full_name", sa.String(length=255)),
            role_column,
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("tenant_id", sa.String(length=64), index=True),
            sa.Column("metadata", sa.Text(), server_default=sa.text("'{}'::text")),
            sa.Column("last_login", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    else:
        # SQLite version
        op.create_table(
            "users",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("email", sa.String(length=255), nullable=False, unique=True),
            sa.Column("username", sa.String(length=64), nullable=False, unique=True),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("full_name", sa.String(length=255)),
            role_column,
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("tenant_id", sa.String(length=64)),
            sa.Column("metadata", sa.Text(), server_default="'{}'"),
            sa.Column("last_login", sa.DateTime()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
    
    # Create api_keys table
    if is_sqlite:
        op.create_table(
            "api_keys",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("key_hash", sa.String(length=255), nullable=False, unique=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("last_used", sa.DateTime()),
            sa.Column("expires_at", sa.DateTime()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
    elif is_postgres:
        op.create_table(
            "api_keys",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("key_hash", sa.String(length=255), nullable=False, unique=True, index=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("last_used", sa.DateTime(timezone=True)),
            sa.Column("expires_at", sa.DateTime(timezone=True)),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
    else:
        op.create_table(
            "api_keys",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("key_hash", sa.String(length=255), nullable=False, unique=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("last_used", sa.DateTime()),
            sa.Column("expires_at", sa.DateTime()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
    
    # Create user_sessions table
    if is_sqlite:
        op.create_table(
            "user_sessions",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("token_hash", sa.String(length=255), nullable=False, unique=True),
            sa.Column("ip_address", sa.String(length=45)),
            sa.Column("user_agent", sa.Text()),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("last_activity", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
    elif is_postgres:
        op.create_table(
            "user_sessions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("token_hash", sa.String(length=255), nullable=False, unique=True, index=True),
            sa.Column("ip_address", sa.String(length=45)),
            sa.Column("user_agent", sa.Text()),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_activity", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
    else:
        op.create_table(
            "user_sessions",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("token_hash", sa.String(length=255), nullable=False, unique=True),
            sa.Column("ip_address", sa.String(length=45)),
            sa.Column("user_agent", sa.Text()),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("last_activity", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
    
    # Create conversations table
    if is_sqlite:
        op.create_table(
            "conversations",
            sa.Column("id", sa.String(length=128), primary_key=True),
            sa.Column("tenant_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.String(length=36)),
            sa.Column("title", sa.String(length=512)),
            sa.Column("metadata", sa.Text(), server_default="'{}'"),
            sa.Column("message_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("last_message_at", sa.DateTime()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        )
    elif is_postgres:
        op.create_table(
            "conversations",
            sa.Column("id", sa.String(length=128), primary_key=True),
            sa.Column("tenant_id", sa.String(length=64), nullable=False, index=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), index=True),
            sa.Column("title", sa.String(length=512)),
            sa.Column("metadata", sa.Text(), server_default=sa.text("'{}'::text")),
            sa.Column("message_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("last_message_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        )
    else:
        op.create_table(
            "conversations",
            sa.Column("id", sa.String(length=128), primary_key=True),
            sa.Column("tenant_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.String(length=36)),
            sa.Column("title", sa.String(length=512)),
            sa.Column("metadata", sa.Text(), server_default="'{}'"),
            sa.Column("message_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("last_message_at", sa.DateTime()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        )
    


def downgrade() -> None:
    op.drop_table("conversations", if_exists=True)
    op.drop_table("user_sessions", if_exists=True)
    op.drop_table("api_keys", if_exists=True)
    op.drop_table("users", if_exists=True)
    
    # Drop enum
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)

