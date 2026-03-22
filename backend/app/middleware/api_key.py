import time
from collections import defaultdict
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.api_key import ApiKey
from app.models.user import User


# Simple in-memory rate limiter: key_id -> list of request timestamps
_rate_limit_windows: dict[str, list[float]] = defaultdict(list)
_WINDOW_SECONDS = 3600  # 1-hour sliding window


def _check_rate_limit(key_id: str, rate_limit: int) -> bool:
    """Check if the API key has exceeded its rate limit within the sliding window."""
    now = time.time()
    window_start = now - _WINDOW_SECONDS

    # Clean old entries
    _rate_limit_windows[key_id] = [
        ts for ts in _rate_limit_windows[key_id] if ts > window_start
    ]

    if len(_rate_limit_windows[key_id]) >= rate_limit:
        return False

    _rate_limit_windows[key_id].append(now)
    return True


async def get_api_key_user(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate API key from X-API-Key header, enforce rate limit, return associated user."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.key == x_api_key, ApiKey.is_active == True)  # noqa: E712
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    # Check rate limit
    if not _check_rate_limit(str(api_key.id), api_key.rate_limit):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {api_key.rate_limit} requests per hour.",
        )

    # Update usage stats
    await db.execute(
        update(ApiKey)
        .where(ApiKey.id == api_key.id)
        .values(
            request_count=ApiKey.request_count + 1,
            last_used_at=datetime.now(timezone.utc),
        )
    )

    # Load associated user
    user_result = await db.execute(select(User).where(User.id == api_key.user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with API key not found",
        )

    return user
