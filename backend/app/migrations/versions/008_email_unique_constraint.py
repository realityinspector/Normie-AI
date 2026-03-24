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

    # Find and NULL out duplicate emails (keep one per email)
    conn.execute(
        text("""
        UPDATE users u SET email = NULL
        FROM (
            SELECT email, MIN(created_at) AS earliest
            FROM users
            WHERE email IS NOT NULL
            GROUP BY email
            HAVING COUNT(*) > 1
        ) dups
        WHERE u.email = dups.email
        AND u.created_at > dups.earliest
    """)
    )

    # Check if constraint already exists (idempotent)
    exists = conn.execute(
        text("SELECT 1 FROM pg_constraint WHERE conname = 'uq_users_email'")
    ).fetchone()
    if not exists:
        op.create_unique_constraint("uq_users_email", "users", ["email"])

    # Check if index already exists
    idx_exists = conn.execute(
        text("SELECT 1 FROM pg_indexes WHERE indexname = 'ix_users_email'")
    ).fetchone()
    if not idx_exists:
        op.create_index("ix_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_constraint("uq_users_email", "users", type_="unique")
