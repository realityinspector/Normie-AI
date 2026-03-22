"""Clean up test users from production database."""

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Delete API keys belonging to test users first (foreign key constraint)
    op.execute(
        "DELETE FROM api_keys WHERE user_id IN ("
        "  SELECT id FROM users WHERE email = 'test-smoke@example.com' OR email LIKE '%@test.dev'"
        ")"
    )
    # Delete credit transactions for test users
    op.execute(
        "DELETE FROM credit_transactions WHERE user_id IN ("
        "  SELECT id FROM users WHERE email = 'test-smoke@example.com' OR email LIKE '%@test.dev'"
        ")"
    )
    # Delete room participants for test users
    op.execute(
        "DELETE FROM room_participants WHERE user_id IN ("
        "  SELECT id FROM users WHERE email = 'test-smoke@example.com' OR email LIKE '%@test.dev'"
        ")"
    )
    # Delete messages from test users
    op.execute(
        "DELETE FROM messages WHERE sender_id IN ("
        "  SELECT id FROM users WHERE email = 'test-smoke@example.com' OR email LIKE '%@test.dev'"
        ")"
    )
    # Delete test users
    op.execute(
        "DELETE FROM users WHERE email = 'test-smoke@example.com' OR email LIKE '%@test.dev'"
    )


def downgrade() -> None:
    # Cannot restore deleted users
    pass
