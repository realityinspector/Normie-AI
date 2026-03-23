import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.user import User, CommunicationStyle
from app.models.credit import CreditTransaction, TransactionType


async def check_access(db: AsyncSession, user: User) -> bool:
    """Check if user has access to the service.

    - Autistic (neurodivergent) users: always free.
    - Users with active, non-expired subscription: unlimited access.
    - Users with credit_balance > 0: access granted (caller handles deduction).
    Raises HTTPException 402 if access is denied.
    """
    if user.communication_style == CommunicationStyle.autistic:
        return True

    if (
        user.subscription_active
        and user.subscription_expires_at is not None
        and user.subscription_expires_at > datetime.now(timezone.utc)
    ):
        return True

    if user.credit_balance > 0:
        return True

    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail="Subscription required. Neurodivergent users get free access.",
    )


async def check_and_deduct(
    db: AsyncSession, user_id: uuid.UUID, amount: int, description: str
) -> int:
    """Check if user has enough credits, deduct them, and return remaining balance.

    Raises HTTPException 402 if insufficient credits.
    """
    result = await db.execute(select(User).where(User.id == user_id).with_for_update())
    user = result.scalar_one()

    if user.credit_balance < amount:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Need {amount}, have {user.credit_balance}.",
        )

    user.credit_balance -= amount

    tx = CreditTransaction(
        user_id=user_id,
        amount=-amount,
        transaction_type=TransactionType.usage,
        description=description,
    )
    db.add(tx)

    return user.credit_balance


async def add_credits(
    db: AsyncSession,
    user_id: uuid.UUID,
    amount: int,
    transaction_type: TransactionType,
    apple_transaction_id: str | None = None,
    description: str | None = None,
) -> int:
    """Add credits to a user's balance and return new balance."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()

    user.credit_balance += amount

    tx = CreditTransaction(
        user_id=user_id,
        amount=amount,
        transaction_type=transaction_type,
        apple_transaction_id=apple_transaction_id,
        description=description,
    )
    db.add(tx)

    return user.credit_balance
