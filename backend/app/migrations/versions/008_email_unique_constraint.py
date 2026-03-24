"""Add unique constraint and index on users.email

Revision ID: 008
Revises: 007
Create Date: 2026-03-22

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Deduplicate: keep earliest account per email, NULL out duplicates
    conn.execute(
        text("""
        UPDATE users SET email = NULL
        WHERE email IS NOT NULL
        AND id NOT IN (
            SELECT MIN(id::text)::uuid FROM users
            WHERE email IS NOT NULL
            GROUP BY email
        )
    """)
    )

    # Check if constraint already exists (idempotent)
    result = conn.execute(
        text("""
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_users_email'
    """)
    )
    if not result.fetchone():
        op.create_unique_constraint("uq_users_email", "users", ["email"])

    # Check if index already exists (idempotent)
    result = conn.execute(
        text("""
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'ix_users_email'
    """)
    )
    if not result.fetchone():
        op.create_index("ix_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_constraint("uq_users_email", "users", type_="unique")
