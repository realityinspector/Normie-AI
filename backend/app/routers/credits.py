from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.credit import CreditTransaction
from app.schemas.credits import (
    CreditBalanceRead,
    VerifyPurchaseRequest,
    ReferralCodeRead,
    RedeemReferralRequest,
)
from app.services.credit_manager import add_credits
from app.services.apple_storekit import verify_jws, JWSVerificationError
from app.config import get_settings
from app.models.credit import TransactionType
import logging

logger = logging.getLogger("normalaizer")

router = APIRouter()

# Product ID -> number of subscription months mapping
PRODUCT_MONTHS = {
    "com.normalaizer.normie.monthly": 1,  # $4.99/month
    "com.normalaizer.normie.yearly": 12,  # $39.99/year
    "com.normalaizer.normie.giftpack10": 10,  # $39.99 gift pack
}

# Legacy product -> credit mapping (kept for backwards compat)
PRODUCT_CREDITS = {
    "com.normalizer.credits.10": 10,
    "com.normalizer.credits.50": 50,
    "com.normalizer.credits.200": 200,
}


def _extend_subscription(user: User, months: int) -> None:
    """Extend a user's subscription by the given number of months."""
    now = datetime.now(timezone.utc)
    base = (
        user.subscription_expires_at
        if user.subscription_expires_at and user.subscription_expires_at > now
        else now
    )
    user.subscription_expires_at = base + timedelta(days=30 * months)
    user.subscription_active = True


@router.get("/balance", response_model=CreditBalanceRead)
async def get_balance(user: User = Depends(get_current_user)):
    return CreditBalanceRead(balance=user.credit_balance)


@router.post("/verify-purchase", response_model=CreditBalanceRead)
async def verify_purchase(
    body: VerifyPurchaseRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify a StoreKit 2 JWS transaction and extend subscription."""
    settings = get_settings()

    try:
        payload = verify_jws(body.jws_transaction, settings.apple_bundle_id)
    except JWSVerificationError as exc:
        logger.warning(
            "Apple StoreKit JWS verification failed: user_id=%s reason=%s",
            user.id,
            exc,
        )
        raise HTTPException(status_code=400, detail="Invalid purchase receipt") from exc

    # Trust the verified payload over the client-supplied product_id.
    verified_product_id = payload.get("productId") or body.product_id
    verified_transaction_id = str(
        payload.get("transactionId") or body.jws_transaction
    )

    # Replay protection — by Apple-issued transaction ID, not JWS string.
    existing = await db.execute(
        select(CreditTransaction).where(
            CreditTransaction.apple_transaction_id == verified_transaction_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Transaction already processed")

    months = PRODUCT_MONTHS.get(verified_product_id)
    credit_amount = PRODUCT_CREDITS.get(verified_product_id)

    if not months and not credit_amount:
        raise HTTPException(status_code=400, detail="Unknown product ID")

    if months:
        # New subscription model: extend subscription
        _extend_subscription(user, months)

        # Record as a credit transaction for audit trail
        tx = CreditTransaction(
            user_id=user.id,
            amount=0,
            transaction_type=TransactionType.purchase,
            apple_transaction_id=verified_transaction_id,
            description=f"Subscription extended by {months} month(s)",
        )
        db.add(tx)
    else:
        # Legacy credit purchase
        await add_credits(
            db,
            user.id,
            credit_amount,
            TransactionType.purchase,
            apple_transaction_id=verified_transaction_id,
            description=f"Purchased {credit_amount} credits",
        )

    return CreditBalanceRead(balance=user.credit_balance)


@router.get("/referral-code", response_model=ReferralCodeRead)
async def get_referral_code(user: User = Depends(get_current_user)):
    """Return the current user's referral code."""
    return ReferralCodeRead(code=user.referral_code)


@router.post("/redeem-referral", response_model=CreditBalanceRead)
async def redeem_referral(
    body: RedeemReferralRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Redeem a referral code. The referrer gets 1 free month added."""
    code = body.referral_code.strip().upper()

    if code == user.referral_code:
        raise HTTPException(
            status_code=400, detail="You cannot redeem your own referral code"
        )

    # Lock the user row to prevent concurrent referral redemption
    result = await db.execute(select(User).where(User.id == user.id).with_for_update())
    locked_user = result.scalar_one()

    if locked_user.referred_by is not None:
        raise HTTPException(
            status_code=400, detail="You have already used a referral code"
        )

    # Find the referrer
    result = await db.execute(select(User).where(User.referral_code == code))
    referrer = result.scalar_one_or_none()
    if not referrer:
        raise HTTPException(status_code=404, detail="Invalid referral code")

    # Mark this user as referred
    locked_user.referred_by = referrer.id

    # Give the referrer 1 free month
    _extend_subscription(referrer, 1)

    return CreditBalanceRead(balance=locked_user.credit_balance)
