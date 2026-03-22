"""Stripe integration service for subscription payments."""

import logging
from datetime import datetime, timezone

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User

logger = logging.getLogger(__name__)


def _configure_stripe() -> None:
    """Set the Stripe API key from settings."""
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key


async def create_checkout_session(
    user: User, price_id: str, db: AsyncSession
) -> stripe.checkout.Session:
    """Create a Stripe Checkout session for the given user and price.

    If the user doesn't have a Stripe customer ID yet, one is created and
    saved to the database.
    """
    _configure_stripe()
    settings = get_settings()

    # Ensure user has a Stripe customer
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": str(user.id)},
        )
        user.stripe_customer_id = customer.id
        await db.flush()

    session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.base_url}/settings?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.base_url}/pricing",
        metadata={"user_id": str(user.id)},
    )
    return session


async def create_customer_portal_session(user: User) -> stripe.billing_portal.Session:
    """Create a Stripe Customer Portal session for subscription management."""
    _configure_stripe()
    settings = get_settings()

    if not user.stripe_customer_id:
        raise ValueError("User does not have a Stripe customer ID")

    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{settings.base_url}/settings",
    )
    return session


async def handle_checkout_completed(
    session: dict, user: User, db: AsyncSession
) -> None:
    """Activate subscription after successful checkout.

    Called when a checkout.session.completed event is received.
    Commits the transaction atomically; rolls back on failure.
    """
    old_active = user.subscription_active
    old_customer_id = user.stripe_customer_id

    try:
        user.subscription_active = True
        # Store the Stripe customer ID if not already set
        customer_id = session.get("customer")
        if customer_id and not user.stripe_customer_id:
            user.stripe_customer_id = customer_id

        await db.commit()

        logger.info(
            "Subscription activated for user %s via checkout session %s "
            "(subscription_active: %s -> True, stripe_customer_id: %s -> %s)",
            user.id,
            session.get("id"),
            old_active,
            old_customer_id,
            user.stripe_customer_id,
        )
    except Exception:
        await db.rollback()
        logger.exception(
            "Failed to commit checkout completion for user %s", user.id
        )
        raise


async def handle_subscription_updated(
    subscription: dict, user: User, db: AsyncSession
) -> None:
    """Update subscription status when Stripe sends an update.

    Called when a customer.subscription.updated event is received.
    Commits the transaction atomically; rolls back on failure.
    """
    old_active = user.subscription_active
    old_expires = getattr(user, "subscription_expires_at", None)
    status = subscription.get("status")

    try:
        if status in ("active", "trialing"):
            user.subscription_active = True
            # Update expiry from current_period_end
            period_end = subscription.get("current_period_end")
            if period_end:
                user.subscription_expires_at = datetime.fromtimestamp(
                    period_end, tz=timezone.utc
                )
        else:
            # past_due, canceled, unpaid, incomplete, incomplete_expired, paused
            user.subscription_active = False

        await db.commit()

        logger.info(
            "Subscription updated for user %s: status=%s "
            "(subscription_active: %s -> %s, expires_at: %s -> %s)",
            user.id,
            status,
            old_active,
            user.subscription_active,
            old_expires,
            getattr(user, "subscription_expires_at", None),
        )
    except Exception:
        await db.rollback()
        logger.exception(
            "Failed to commit subscription update for user %s", user.id
        )
        raise


async def handle_subscription_deleted(
    subscription: dict, user: User, db: AsyncSession
) -> None:
    """Deactivate subscription when it is canceled/deleted.

    Called when a customer.subscription.deleted event is received.
    Commits the transaction atomically; rolls back on failure.
    """
    old_active = user.subscription_active

    try:
        user.subscription_active = False

        await db.commit()

        logger.info(
            "Subscription deleted for user %s (subscription %s, "
            "subscription_active: %s -> False)",
            user.id,
            subscription.get("id"),
            old_active,
        )
    except Exception:
        await db.rollback()
        logger.exception(
            "Failed to commit subscription deletion for user %s", user.id
        )
        raise
