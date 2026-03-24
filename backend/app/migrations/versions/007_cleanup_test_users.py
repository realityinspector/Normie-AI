"""Clean up test users from production database."""

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Delete in FK-safe order for test users
    test_filter = "email = 'test-smoke@example.com' OR email LIKE '%@test.dev'"

    # Delete API keys
    op.execute(
        f"DELETE FROM api_keys WHERE user_id IN (SELECT id FROM users WHERE {test_filter})"
    )
    # Delete credit transactions
    op.execute(
        f"DELETE FROM credit_transactions WHERE user_id IN (SELECT id FROM users WHERE {test_filter})"
    )
    # Delete transcripts for rooms owned by test users
    op.execute(
        f"DELETE FROM transcripts WHERE room_id IN (SELECT id FROM rooms WHERE owner_id IN (SELECT id FROM users WHERE {test_filter}))"
    )
    # Delete messages in rooms owned by test users
    op.execute(
        f"DELETE FROM messages WHERE room_id IN (SELECT id FROM rooms WHERE owner_id IN (SELECT id FROM users WHERE {test_filter}))"
    )
    # Delete room participants for test users (as participant)
    op.execute(
        f"DELETE FROM room_participants WHERE user_id IN (SELECT id FROM users WHERE {test_filter})"
    )
    # Delete room participants in rooms owned by test users
    op.execute(
        f"DELETE FROM room_participants WHERE room_id IN (SELECT id FROM rooms WHERE owner_id IN (SELECT id FROM users WHERE {test_filter}))"
    )
    # Delete rooms owned by test users
    op.execute(
        f"DELETE FROM rooms WHERE owner_id IN (SELECT id FROM users WHERE {test_filter})"
    )
    # Delete test users
    op.execute(f"DELETE FROM users WHERE {test_filter}")


def downgrade() -> None:
    pass
