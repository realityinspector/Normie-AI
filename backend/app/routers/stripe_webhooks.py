"""Stripe webhook endpoint for processing subscription events."""

import logging

import stripe
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.services.stripe_service import (
    handle_checkout_completed,
    handle_subscription_updated,
    handle_subscription_deleted,
)

logger = logging.getLogger("normalaizer")

router = APIRouter()


async def _get_user_by_stripe_customer(
    customer_id: str, db: AsyncSession
) -> User | None:
    """Look up a user by their Stripe customer ID."""
    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    return result.scalar_one_or_none()


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive and process Stripe webhook events.

    Verifies the webhook signature, then dispatches to the appropriate handler
    based on the event type. Always returns 200 for valid events to prevent
    Stripe retry loops, even if handler processing fails.
    """
    settings = get_settings()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        logger.warning("Invalid Stripe webhook payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError:
        logger.warning("Invalid Stripe webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data_object = event["data"]["object"]

    logger.info("Received Stripe event: %s (id=%s)", event_type, event.get("id"))

    try:
        if event_type == "checkout.session.completed":
            customer_id = data_object.get("customer")
            if not customer_id:
                logger.warning("checkout.session.completed without customer ID")
                return {"status": "ignored"}

            user = await _get_user_by_stripe_customer(customer_id, db)
            if not user:
                logger.warning("No user found for Stripe customer %s", customer_id)
                return {"status": "ignored"}

            await handle_checkout_completed(data_object, user, db)

        elif event_type == "customer.subscription.updated":
            customer_id = data_object.get("customer")
            if not customer_id:
                return {"status": "ignored"}

            user = await _get_user_by_stripe_customer(customer_id, db)
            if not user:
                logger.warning("No user found for Stripe customer %s", customer_id)
                return {"status": "ignored"}

            await handle_subscription_updated(data_object, user, db)

        elif event_type == "customer.subscription.deleted":
            customer_id = data_object.get("customer")
            if not customer_id:
                return {"status": "ignored"}

            user = await _get_user_by_stripe_customer(customer_id, db)
            if not user:
                logger.warning("No user found for Stripe customer %s", customer_id)
                return {"status": "ignored"}

            await handle_subscription_deleted(data_object, user, db)

        else:
            logger.debug("Unhandled Stripe event type: %s", event_type)

    except Exception:
        # Log the error but return 200 to prevent Stripe retry loops.
        # The error is already logged by the service layer; add context here.
        logger.exception(
            "Error processing Stripe event %s (id=%s). "
            "Returning 200 to prevent retry loop.",
            event_type,
            event.get("id"),
        )
        return {"status": "error", "message": "Handler failed but acknowledged"}

    return {"status": "ok"}
