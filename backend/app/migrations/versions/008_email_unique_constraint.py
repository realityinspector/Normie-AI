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
    # First, deduplicate any emails that would violate the unique constraint
    # Keep the earliest account for each duplicate email, NULL out the rest
    conn = op.get_bind()
    conn.execute(
        text("""
        UPDATE users SET email = NULL
        WHERE id NOT IN (
            SELECT MIN(id) FROM users
            WHERE email IS NOT NULL
            GROUP BY email
        )
        AND email IS NOT NULL
    """)
    )

    # Now safe to add unique constraint (NULLs are allowed and distinct in PostgreSQL)
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_index("ix_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_constraint("uq_users_email", "users", type_="unique")
