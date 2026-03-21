"""Initial database schema

Revision ID: 001
Revises: None
Create Date: 2026-03-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("apple_sub", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False, server_default="User"),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column(
            "communication_style",
            sa.Enum("neurotypical", "autistic", name="communicationstyle"),
            nullable=False,
            server_default="neurotypical",
        ),
        sa.Column("credit_balance", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("apple_sub"),
    )
    op.create_index("ix_users_apple_sub", "users", ["apple_sub"])

    # Rooms
    op.create_table(
        "rooms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Room Participants
    op.create_table(
        "room_participants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("room_id", sa.Uuid(), sa.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_id", "user_id"),
    )

    # Messages
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("room_id", sa.Uuid(), sa.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("original_text", sa.String(), nullable=False),
        sa.Column("translations", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_room_id", "messages", ["room_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])

    # Transcripts
    op.create_table(
        "transcripts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("room_id", sa.Uuid(), sa.ForeignKey("rooms.id"), nullable=False),
        sa.Column("room_name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(16), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_transcripts_slug", "transcripts", ["slug"])

    # Credit Transactions
    op.create_table(
        "credit_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column(
            "transaction_type",
            sa.Enum("purchase", "usage", "bonus", name="transactiontype"),
            nullable=False,
        ),
        sa.Column("apple_transaction_id", sa.String(255), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("apple_transaction_id"),
    )
    op.create_index("ix_credit_transactions_user_id", "credit_transactions", ["user_id"])


def downgrade() -> None:
    op.drop_table("credit_transactions")
    op.drop_table("transcripts")
    op.drop_table("messages")
    op.drop_table("room_participants")
    op.drop_table("rooms")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS communicationstyle")
    op.execute("DROP TYPE IF EXISTS transactiontype")
