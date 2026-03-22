import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AppleSignInRequest,
    GoogleSignInRequest,
    LoginRequest,
    SignupRequest,
    TokenResponse,
)
from pydantic import BaseModel
from app.services.apple_auth import verify_apple_identity_token

logger = logging.getLogger(__name__)

# Simple in-memory rate limiter for auth endpoints
_auth_rate_limits: dict[str, list[float]] = defaultdict(list)
_AUTH_RATE_LIMIT = 10  # max requests
_AUTH_RATE_WINDOW = 60  # per 60 seconds


def _check_rate_limit(ip: str) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    now = time.time()
    # Clean old entries
    _auth_rate_limits[ip] = [
        t for t in _auth_rate_limits[ip] if now - t < _AUTH_RATE_WINDOW
    ]
    if len(_auth_rate_limits[ip]) >= _AUTH_RATE_LIMIT:
        return False
    _auth_rate_limits[ip].append(now)
    return True


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


def _set_session_cookie(response: Response, token: str, expires_in: int) -> None:
    """Set an HttpOnly session cookie containing the JWT."""
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=expires_in,
        path="/",
    )


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


@router.post("/signup", response_model=TokenResponse)
async def signup(
    body: SignupRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Create a new user with email and password."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429, detail="Too many requests. Try again in a minute."
        )

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == body.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    settings = get_settings()
    user = User(
        display_name=body.display_name,
        email=body.email,
        password_hash=_hash_password(body.password),
        credit_balance=settings.initial_credits,
    )
    db.add(user)
    await db.flush()

    token, expires_in = _create_token(str(user.id))
    _set_session_cookie(response, token, expires_in)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email and password."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429, detail="Too many requests. Try again in a minute."
        )

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not _verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token, expires_in = _create_token(str(user.id))
    _set_session_cookie(response, token, expires_in)
    return TokenResponse(access_token=token, expires_in=expires_in)


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


@router.post("/google", response_model=TokenResponse)
async def google_sign_in(
    request: GoogleSignInRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a Google ID token for an app JWT + session cookie."""
    import httpx

    settings = get_settings()
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google Sign-In is not configured",
        )

    # Verify the ID token with Google's tokeninfo endpoint
    async with httpx.AsyncClient() as client:
        google_resp = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": request.credential},
        )

    if google_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token",
        )

    token_info = google_resp.json()

    # Verify the token was issued for our client ID
    if token_info.get("aud") != settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google token audience mismatch",
        )

    google_sub = token_info.get("sub")
    email = token_info.get("email")
    name = token_info.get("name", "User")

    if not google_sub or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google token missing required claims",
        )

    # Try to find user by google_sub first
    result = await db.execute(select(User).where(User.google_sub == google_sub))
    user = result.scalar_one_or_none()

    if not user:
        # Try to find by email (link existing account)
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            # Link Google identity to existing account
            user.google_sub = google_sub
        else:
            # Create new user
            user = User(
                google_sub=google_sub,
                display_name=name,
                email=email,
                credit_balance=settings.initial_credits,
            )
            db.add(user)

    await db.flush()

    token, expires_in = _create_token(str(user.id))
    _set_session_cookie(response, token, expires_in)
    return TokenResponse(access_token=token, expires_in=expires_in)


# --- Dev/Test auth (remove before App Store submission) ---


class DevSignInRequest(BaseModel):
    name: str
    communication_style: str = "neurotypical"


@router.post("/dev", response_model=TokenResponse)
async def dev_sign_in(
    body: DevSignInRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """DEV ONLY: Create a test user without Apple Sign-In. Gated by DEV_AUTH_ENABLED env var."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429, detail="Too many requests. Try again in a minute."
        )

    settings = get_settings()
    if settings.dev_auth_enabled != "true":
        raise HTTPException(status_code=404, detail="Not found")
    logger.warning("DEV AUTH ENDPOINT IS ENABLED — DO NOT USE IN PRODUCTION")
    import hashlib

    fake_sub = "dev_" + hashlib.sha256(body.name.encode()).hexdigest()[:16]

    result = await db.execute(select(User).where(User.apple_sub == fake_sub))
    user = result.scalar_one_or_none()

    if not user:
        from app.models.user import CommunicationStyle

        style = (
            CommunicationStyle.autistic
            if body.communication_style == "autistic"
            else CommunicationStyle.neurotypical
        )
        settings = get_settings()
        user = User(
            apple_sub=fake_sub,
            display_name=body.name,
            email=f"{body.name.lower().replace(' ', '.')}@test.dev",
            communication_style=style,
            credit_balance=settings.initial_credits,
        )
        db.add(user)
        await db.flush()

    token, expires_in = _create_token(str(user.id))
    return TokenResponse(access_token=token, expires_in=expires_in)
