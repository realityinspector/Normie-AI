from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import AppleSignInRequest, TokenResponse
from app.services.apple_auth import verify_apple_identity_token

router = APIRouter()


def _create_token(user_id: str) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.jwt_expiry_hours * 3600
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


@router.post("/apple", response_model=TokenResponse)
async def apple_sign_in(
    request: AppleSignInRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange an Apple identity token for an app JWT."""
    try:
        claims = await verify_apple_identity_token(request.identity_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Apple identity token: {e}",
        )

    apple_sub = claims["sub"]
    email = claims.get("email")

    # Find or create user
    result = await db.execute(select(User).where(User.apple_sub == apple_sub))
    user = result.scalar_one_or_none()

    if not user:
        settings = get_settings()
        user = User(
            apple_sub=apple_sub,
            display_name=request.full_name or "User",
            email=email,
            credit_balance=settings.initial_credits,
        )
        db.add(user)
        await db.flush()

    token, expires_in = _create_token(str(user.id))
    return TokenResponse(access_token=token, expires_in=expires_in)


# --- Dev/Test auth (remove before App Store submission) ---
from pydantic import BaseModel


class DevSignInRequest(BaseModel):
    name: str
    communication_style: str = "neurotypical"


@router.post("/dev", response_model=TokenResponse)
async def dev_sign_in(
    request: DevSignInRequest,
    db: AsyncSession = Depends(get_db),
):
    """DEV ONLY: Create a test user without Apple Sign-In. Gated by DEV_AUTH_ENABLED env var."""
    settings = get_settings()
    if settings.dev_auth_enabled != "true":
        raise HTTPException(status_code=404, detail="Not found")
    import hashlib
    fake_sub = "dev_" + hashlib.sha256(request.name.encode()).hexdigest()[:16]

    result = await db.execute(select(User).where(User.apple_sub == fake_sub))
    user = result.scalar_one_or_none()

    if not user:
        from app.models.user import CommunicationStyle
        style = CommunicationStyle.autistic if request.communication_style == "autistic" else CommunicationStyle.neurotypical
        settings = get_settings()
        user = User(
            apple_sub=fake_sub,
            display_name=request.name,
            email=f"{request.name.lower().replace(' ', '.')}@test.dev",
            communication_style=style,
            credit_balance=settings.initial_credits,
        )
        db.add(user)
        await db.flush()

    token, expires_in = _create_token(str(user.id))
    return TokenResponse(access_token=token, expires_in=expires_in)
