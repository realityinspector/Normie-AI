"""Pages router – serves HTML templates for the web frontend."""

import pathlib
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import jwt as pyjwt

from app.config import get_settings
from app.database import async_session
from app.models.transcript import Transcript
from app.models.message import Message
from app.models.room import Room, RoomParticipant

from app.middleware.auth import get_current_user
from app.models.user import User

_TEMPLATES_DIR = pathlib.Path(__file__).resolve().parent.parent / "templates"

router = APIRouter()
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _get_session_user(request: Request) -> dict | None:
    """Extract user info from the session cookie JWT. Returns None if invalid."""
    token = request.cookies.get("session")
    if not token:
        return None
    settings = get_settings()
    try:
        payload = pyjwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return {
            "user_id": payload["sub"],
            "token": token,
        }
    except Exception:
        return None


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    """Marketing landing page with signup CTA."""
    return templates.TemplateResponse("pages/landing.html", {"request": request})


@router.get("/developers", response_class=HTMLResponse)
async def developers(request: Request, user: User = Depends(get_current_user)):
    """Developer documentation and API key management page."""
    base_url = str(request.base_url).rstrip("/")
    return templates.TemplateResponse(
        "pages/developers.html",
        {"request": request, "user": user, "base_url": base_url},
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page with email/password form."""
    settings = get_settings()
    next_url = request.query_params.get("next", "")
    return templates.TemplateResponse(
        "pages/login.html",
        {
            "request": request,
            "google_client_id": settings.google_client_id,
            "next_url": next_url,
        },
    )


@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """Signup page with registration form."""
    settings = get_settings()
    next_url = request.query_params.get("next", "")
    return templates.TemplateResponse(
        "pages/signup.html",
        {
            "request": request,
            "google_client_id": settings.google_client_id,
            "next_url": next_url,
        },
    )


@router.get("/app", response_class=HTMLResponse)
async def app_page(request: Request):
    """Main chat application page. Requires auth — redirects to /login if no session."""
    session = _get_session_user(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    # Fetch display_name from DB for template context
    display_name = await _get_display_name(session["user_id"])

    return templates.TemplateResponse(
        "pages/app.html",
        {
            "request": request,
            "token": session["token"],
            "user_id": session["user_id"],
            "display_name": display_name,
            "initial_room_id": None,
        },
    )


@router.get("/app/room/{room_id}", response_class=HTMLResponse)
async def app_room_page(request: Request, room_id: uuid.UUID):
    """Chat app with a specific room pre-selected. Requires auth."""
    session = _get_session_user(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    display_name = await _get_display_name(session["user_id"])

    return templates.TemplateResponse(
        "pages/app.html",
        {
            "request": request,
            "token": session["token"],
            "user_id": session["user_id"],
            "display_name": display_name,
            "initial_room_id": str(room_id),
        },
    )


async def _get_display_name(user_id_str: str) -> str:
    """Fetch user display name from the database."""
    from sqlalchemy import select
    from app.models.user import User

    try:
        uid = uuid.UUID(user_id_str)
        async with async_session() as db:
            result = await db.execute(select(User.display_name).where(User.id == uid))
            row = result.scalar_one_or_none()
            return row or "User"
    except Exception:
        return "User"


async def _get_user_by_id(user_id_str: str) -> User | None:
    """Fetch a full User object from the database by ID."""
    from sqlalchemy import select
    from app.database import async_session

    try:
        uid = uuid.UUID(user_id_str)
        async with async_session() as db:
            result = await db.execute(select(User).where(User.id == uid))
            return result.scalar_one_or_none()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Pricing page (public)
# ---------------------------------------------------------------------------


@router.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request):
    """Subscription pricing page with plan selection and checkout."""
    settings = get_settings()
    return templates.TemplateResponse(
        "pages/pricing.html",
        {
            "request": request,
            "monthly_price_id": settings.stripe_monthly_price_id,
            "yearly_price_id": settings.stripe_yearly_price_id,
        },
    )


# ---------------------------------------------------------------------------
# Settings page (auth required)
# ---------------------------------------------------------------------------


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """User settings page with profile, subscription, and referral info."""
    session = _get_session_user(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    user = await _get_user_by_id(session["user_id"])
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        "pages/settings.html",
        {
            "request": request,
            "user": user,
        },
    )


# ─── Share Pages ───


@router.get("/t/{slug}", response_class=HTMLResponse)
async def public_transcript(request: Request, slug: str):
    """Public transcript view with OG meta tags for social sharing."""
    settings = get_settings()

    async with async_session() as db:
        # Fetch transcript by slug
        result = await db.execute(select(Transcript).where(Transcript.slug == slug))
        transcript = result.scalar_one_or_none()

        if not transcript:
            return HTMLResponse(
                content="<h1>Transcript not found</h1><p><a href='/'>Go home</a></p>",
                status_code=404,
            )

        # Fetch messages with sender info
        msg_result = await db.execute(
            select(Message)
            .where(Message.room_id == transcript.room_id)
            .order_by(Message.created_at.asc())
            .options(selectinload(Message.sender))
        )
        messages_raw = msg_result.scalars().all()

        messages = []
        for msg in messages_raw:
            messages.append(
                {
                    "sender_name": msg.sender.display_name if msg.sender else "Unknown",
                    "sender_id": str(msg.sender_id),
                    "original_text": msg.original_text,
                    "created_at": msg.created_at,
                    "is_owner": str(msg.sender_id) == str(transcript.user_id),
                }
            )

    return templates.TemplateResponse(
        "share/transcript.html",
        {
            "request": request,
            "transcript": transcript,
            "messages": messages,
            "base_url": settings.base_url.rstrip("/"),
        },
    )


@router.get("/r/{room_id}/invite", response_class=HTMLResponse)
async def room_invite(request: Request, room_id: uuid.UUID):
    """Room invite page with OG meta tags for social sharing."""
    settings = get_settings()

    async with async_session() as db:
        # Fetch room
        result = await db.execute(select(Room).where(Room.id == room_id))
        room = result.scalar_one_or_none()

        if not room:
            return HTMLResponse(
                content=(
                    "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
                    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                    "<script src='https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4'></script>"
                    "<title>Room Not Found</title></head>"
                    "<body class='bg-gray-100 min-h-screen flex items-center justify-center'>"
                    "<div class='text-center px-6'>"
                    "<p class='text-5xl mb-4'>🔍</p>"
                    "<h1 class='text-xl font-bold text-gray-800 mb-2'>Room not found</h1>"
                    "<p class='text-sm text-gray-500 mb-6'>This room may have been deleted or the link is invalid.</p>"
                    "<a href='/' class='px-6 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700'>Go Home</a>"
                    "</div></body></html>"
                ),
                status_code=404,
            )

        # Count participants
        count_result = await db.execute(
            select(func.count())
            .select_from(RoomParticipant)
            .where(RoomParticipant.room_id == room_id)
        )
        participant_count = count_result.scalar() or 0

    return templates.TemplateResponse(
        "share/room_invite.html",
        {
            "request": request,
            "room": room,
            "participant_count": participant_count,
            "base_url": settings.base_url.rstrip("/"),
        },
    )


@router.get("/r/{room_id}/join")
async def room_join(request: Request, room_id: uuid.UUID):
    """Join a room via invite link. Redirects unauthenticated users to signup."""
    session = _get_session_user(request)
    if not session:
        return RedirectResponse(url=f"/signup?next=/r/{room_id}/join", status_code=302)

    # Auto-join the user to the room
    async with async_session() as db:
        result = await db.execute(select(Room).where(Room.id == room_id))
        room = result.scalar_one_or_none()

        if not room:
            return HTMLResponse(
                content=(
                    "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
                    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                    "<script src='https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4'></script>"
                    "<title>Room Not Found</title></head>"
                    "<body class='bg-gray-100 min-h-screen flex items-center justify-center'>"
                    "<div class='text-center px-6'>"
                    "<p class='text-5xl mb-4'>🔍</p>"
                    "<h1 class='text-xl font-bold text-gray-800 mb-2'>Room not found</h1>"
                    "<p class='text-sm text-gray-500 mb-6'>This room may have been deleted or the link is invalid.</p>"
                    "<a href='/' class='px-6 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700'>Go Home</a>"
                    "</div></body></html>"
                ),
                status_code=404,
            )

        uid = uuid.UUID(session["user_id"])

        # Check if already a participant
        existing = await db.execute(
            select(RoomParticipant).where(
                RoomParticipant.room_id == room_id,
                RoomParticipant.user_id == uid,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(RoomParticipant(room_id=room_id, user_id=uid))
            await db.commit()

    return RedirectResponse(url=f"/app/room/{room_id}", status_code=302)
