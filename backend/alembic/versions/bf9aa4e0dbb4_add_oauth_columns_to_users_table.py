"""Add OAuth columns to users table

Revision ID: bf9aa4e0dbb4
Revises: 20251208_02
Create Date: 2025-12-08 12:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bf9aa4e0dbb4'
down_revision = '20251208_02'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    is_sqlite = bind.dialect.name == "sqlite"
    
    # Add OAuth columns to users table
    if is_sqlite:
        # SQLite - add columns with nullable=True
        op.add_column('users', sa.Column('oauth_provider', sa.String(length=32), nullable=True))
        op.add_column('users', sa.Column('oauth_id', sa.String(length=255), nullable=True))
        op.add_column('users', sa.Column('avatar_url', sa.String(length=512), nullable=True))
        
        # Create indexes for SQLite
        op.create_index('ix_users_oauth_provider', 'users', ['oauth_provider'])
        op.create_index('ix_users_oauth_id', 'users', ['oauth_id'])
    elif is_postgres:
        # PostgreSQL
        op.add_column('users', sa.Column('oauth_provider', sa.String(length=32), nullable=True))
        op.add_column('users', sa.Column('oauth_id', sa.String(length=255), nullable=True))
        op.add_column('users', sa.Column('avatar_url', sa.String(length=512), nullable=True))
        
        # Create indexes for PostgreSQL
        op.create_index('ix_users_oauth_provider', 'users', ['oauth_provider'])
        op.create_index('ix_users_oauth_id', 'users', ['oauth_id'])


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    
    # Drop indexes first
    op.drop_index('ix_users_oauth_id', table_name='users')
    op.drop_index('ix_users_oauth_provider', table_name='users')
    
    # Drop columns
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'oauth_id')
    op.drop_column('users', 'oauth_provider')
