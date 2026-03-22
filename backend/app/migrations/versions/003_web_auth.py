"""Add password_hash column and make apple_sub nullable for web auth

Revision ID: 003
Revises: 002
Create Date: 2026-03-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add password_hash column (nullable — existing Apple Sign-In users won't have one)
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(255), nullable=True),
    )

    # Make apple_sub nullable so email/password users don't need one
    op.alter_column(
        "users",
        "apple_sub",
        existing_type=sa.String(255),
        nullable=True,
    )


def downgrade() -> None:
    # Restore apple_sub to non-nullable (backfill NULLs first to avoid errors)
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE users SET apple_sub = 'removed_' || id::text WHERE apple_sub IS NULL")
    )
    op.alter_column(
        "users",
        "apple_sub",
        existing_type=sa.String(255),
        nullable=False,
    )

    op.drop_column("users", "password_hash")
