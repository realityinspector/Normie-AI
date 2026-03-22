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

logger = logging.getLogger(__name__)

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
    based on the event type.
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
    except stripe.error.SignatureVerificationError:
        logger.warning("Invalid Stripe webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data_object = event["data"]["object"]

    logger.info("Received Stripe event: %s (id=%s)", event_type, event.get("id"))

    if event_type == "checkout.session.completed":
        customer_id = data_object.get("customer")
        if not customer_id:
            # Try metadata fallback
            logger.warning("checkout.session.completed without customer ID")
            return {"status": "ignored"}

        user = await _get_user_by_stripe_customer(customer_id, db)
        if not user:
            logger.warning("No user found for Stripe customer %s", customer_id)
            return {"status": "ignored"}

        handle_checkout_completed(data_object, user)

    elif event_type == "customer.subscription.updated":
        customer_id = data_object.get("customer")
        if not customer_id:
            return {"status": "ignored"}

        user = await _get_user_by_stripe_customer(customer_id, db)
        if not user:
            logger.warning("No user found for Stripe customer %s", customer_id)
            return {"status": "ignored"}

        handle_subscription_updated(data_object, user)

    elif event_type == "customer.subscription.deleted":
        customer_id = data_object.get("customer")
        if not customer_id:
            return {"status": "ignored"}

        user = await _get_user_by_stripe_customer(customer_id, db)
        if not user:
            logger.warning("No user found for Stripe customer %s", customer_id)
            return {"status": "ignored"}

        handle_subscription_deleted(data_object, user)

    else:
        logger.debug("Unhandled Stripe event type: %s", event_type)

    return {"status": "ok"}
