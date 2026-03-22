"""Stripe Checkout and Customer Portal endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.stripe_service import create_checkout_session, create_customer_portal_session

logger = logging.getLogger(__name__)

router = APIRouter()


class CheckoutRequest(BaseModel):
    price_id: str


@router.post("/create-checkout-session")
async def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout Session and return the redirect URL.

    The frontend redirects the user to the returned URL to complete payment
    on Stripe's hosted checkout page.
    """
    try:
        session = await create_checkout_session(user, body.price_id, db)
        return {"url": session.url}
    except Exception as exc:
        logger.error("Failed to create checkout session: %s", exc)
        raise HTTPException(status_code=500, detail="Could not create checkout session. Please try again.")


@router.post("/create-portal-session")
async def create_portal(
    user: User = Depends(get_current_user),
):
    """Create a Stripe Customer Portal session and return the redirect URL.

    Users can manage their subscription (upgrade, downgrade, cancel) and
    update payment methods through the portal.
    """
    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No billing account found. Please subscribe first.",
        )
    try:
        session = await create_customer_portal_session(user)
        return {"url": session.url}
    except Exception as exc:
        logger.error("Failed to create portal session: %s", exc)
        raise HTTPException(status_code=500, detail="Could not open billing portal. Please try again.")
