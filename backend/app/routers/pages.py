"""Pages router – serves HTML templates for the web frontend."""

import pathlib
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import jwt as pyjwt

from app.config import get_settings

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
    from app.database import async_session
    from app.models.user import User

    try:
        uid = uuid.UUID(user_id_str)
        async with async_session() as db:
            result = await db.execute(select(User.display_name).where(User.id == uid))
            row = result.scalar_one_or_none()
            return row or "User"
    except Exception:
        return "User"
