import logging
import time
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

logger = logging.getLogger("normalaizer")

router = APIRouter()

# Simple in-memory rate limiter: IP -> list of timestamps
_rate_limits: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 60  # max events per minute per IP
_WINDOW = 60  # seconds


class AnalyticsEvent(BaseModel):
    event: str
    page: Optional[str] = None
    metadata: Optional[dict] = None
    # Legacy alias kept for backward compat
    properties: Optional[dict] = None


def _is_rate_limited(ip: str) -> bool:
    now = time.time()
    timestamps = _rate_limits[ip]
    # Prune old entries
    cutoff = now - _WINDOW
    _rate_limits[ip] = [t for t in timestamps if t > cutoff]
    if len(_rate_limits[ip]) >= _RATE_LIMIT:
        return True
    _rate_limits[ip].append(now)
    return False


def _get_user_id_from_cookie(request: Request) -> str | None:
    """Try to extract user id from the session JWT cookie. Returns None on failure."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        import jwt as pyjwt
        from app.config import get_settings

        settings = get_settings()
        payload = pyjwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload.get("sub") or payload.get("user_id")
    except Exception:
        return None


@router.post("/analytics/event", status_code=status.HTTP_204_NO_CONTENT)
async def track_event(body: AnalyticsEvent, request: Request):
    ip = request.client.host if request.client else "unknown"
    if _is_rate_limited(ip):
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    user_id = _get_user_id_from_cookie(request)
    props = body.metadata or body.properties
    logger.info(
        "analytics event=%s page=%s user=%s ip=%s metadata=%s",
        body.event,
        body.page,
        user_id,
        ip,
        props,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
