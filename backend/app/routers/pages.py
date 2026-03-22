"""Pages router – serves HTML templates for the web frontend."""

import pathlib

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

_TEMPLATES_DIR = pathlib.Path(__file__).resolve().parent.parent / "templates"

router = APIRouter()
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    """Marketing landing page with signup CTA."""
    return templates.TemplateResponse("pages/landing.html", {"request": request})
