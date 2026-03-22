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
        payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
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
    return templates.TemplateResponse("pages/login.html", {"request": request})


@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """Signup page with registration form."""
    return templates.TemplateResponse("pages/signup.html", {"request": request})


@router.get("/app", response_class=HTMLResponse)
async def app_page(request: Request):
    """Main chat application page. Requires auth — redirects to /login if no session."""
    session = _get_session_user(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    # Fetch display_name from DB for template context
    display_name = await _get_display_name(session["user_id"])

    return templates.TemplateResponse("pages/app.html", {
        "request": request,
        "token": session["token"],
        "user_id": session["user_id"],
        "display_name": display_name,
        "initial_room_id": None,
    })


@router.get("/app/room/{room_id}", response_class=HTMLResponse)
async def app_room_page(request: Request, room_id: uuid.UUID):
    """Chat app with a specific room pre-selected. Requires auth."""
    session = _get_session_user(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    display_name = await _get_display_name(session["user_id"])

    return templates.TemplateResponse("pages/app.html", {
        "request": request,
        "token": session["token"],
        "user_id": session["user_id"],
        "display_name": display_name,
        "initial_room_id": str(room_id),
    })


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
            messages.append({
                "sender_name": msg.sender.display_name if msg.sender else "Unknown",
                "sender_id": str(msg.sender_id),
                "original_text": msg.original_text,
                "created_at": msg.created_at,
                "is_owner": str(msg.sender_id) == str(transcript.user_id),
            })

    return templates.TemplateResponse("share/transcript.html", {
        "request": request,
        "transcript": transcript,
        "messages": messages,
        "base_url": settings.base_url.rstrip("/"),
    })


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
                content="<h1>Room not found</h1><p><a href='/'>Go home</a></p>",
                status_code=404,
            )

        # Count participants
        count_result = await db.execute(
            select(func.count())
            .select_from(RoomParticipant)
            .where(RoomParticipant.room_id == room_id)
        )
        participant_count = count_result.scalar() or 0

    return templates.TemplateResponse("share/room_invite.html", {
        "request": request,
        "room": room,
        "participant_count": participant_count,
        "base_url": settings.base_url.rstrip("/"),
    })
