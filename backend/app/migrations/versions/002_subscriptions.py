"""Add subscription and referral fields to users

Revision ID: 002
Revises: 001
Create Date: 2026-03-18

"""
import string
import secrets
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _generate_referral_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


def upgrade() -> None:
    # Add subscription_active column
    op.add_column(
        "users",
        sa.Column("subscription_active", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Add subscription_expires_at column
    op.add_column(
        "users",
        sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add referral_code column (nullable first, then backfill, then make non-nullable)
    op.add_column(
        "users",
        sa.Column("referral_code", sa.String(8), nullable=True),
    )

    # Add referred_by column
    op.add_column(
        "users",
        sa.Column("referred_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
    )

    # Backfill referral codes for existing users
    conn = op.get_bind()
    users = conn.execute(sa.text("SELECT id FROM users WHERE referral_code IS NULL"))
    for row in users:
        code = _generate_referral_code()
        conn.execute(
            sa.text("UPDATE users SET referral_code = :code WHERE id = :uid"),
            {"code": code, "uid": row[0]},
        )

    # Now make referral_code non-nullable and add unique constraint / index
    op.alter_column("users", "referral_code", nullable=False)
    op.create_unique_constraint("uq_users_referral_code", "users", ["referral_code"])
    op.create_index("ix_users_referral_code", "users", ["referral_code"])


def downgrade() -> None:
    op.drop_index("ix_users_referral_code", table_name="users")
    op.drop_constraint("uq_users_referral_code", "users", type_="unique")
    op.drop_column("users", "referred_by")
    op.drop_column("users", "referral_code")
    op.drop_column("users", "subscription_expires_at")
    op.drop_column("users", "subscription_active")
