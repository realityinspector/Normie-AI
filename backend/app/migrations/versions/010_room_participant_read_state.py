"""Track last-read timestamp per room participant for read receipts.

Revision ID: 010
Revises: 009
Create Date: 2026-04-22

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "room_participants",
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("room_participants", "last_read_at")
