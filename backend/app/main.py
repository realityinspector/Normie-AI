import logging
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.routers import (
    auth,
    users,
    rooms,
    messages,
    translate,
    transcripts,
    credits,
    ws,
    pages,
    api_v1,
    stripe_webhooks,
    stripe_checkout,
)
from app.routers.integrations import router as integrations_router

# Resolve paths relative to this file
_APP_DIR = pathlib.Path(__file__).resolve().parent
_STATIC_DIR = _APP_DIR / "static"
_TEMPLATES_DIR = _APP_DIR / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger("normalaizer")
    settings = get_settings()
    if not settings.jwt_secret or len(settings.jwt_secret) < 16:
        logger.warning(
            "JWT_SECRET is too short — use a strong random secret in production!"
        )
    if settings.dev_auth_enabled == "true":
        logger.warning("DEV_AUTH_ENABLED is true — disable in production!")
    yield


app = FastAPI(
    title="NORMALIZER API",
    description="Cultural communication translation API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(404)
async def custom_404(request, exc):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return HTMLResponse(
            content=(
                "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                "<script src='https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4'></script>"
                "<link rel='icon' href=\"data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🧠</text></svg>\" />"
                "<title>Page Not Found – NORMALAIZER</title></head>"
                "<body class='bg-gray-100 min-h-screen flex items-center justify-center'>"
                "<div class='text-center px-6'>"
                "<p class='text-6xl mb-4'>🧠</p>"
                "<h1 class='text-xl font-bold text-gray-800 mb-2'>Page not found</h1>"
                "<p class='text-sm text-gray-500 mb-6'>The page you're looking for doesn't exist.</p>"
                "<a href='/' class='px-6 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 transition'>Go Home</a>"
                "</div></body></html>"
            ),
            status_code=404,
        )
    return JSONResponse(status_code=404, content={"detail": "Not found"})


settings = get_settings()
cors_origins = (
    [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if settings.cors_origins
    else [settings.base_url]
)
# Always allow localhost for dev
if "http://localhost:8000" not in cors_origins:
    cors_origins.append("http://localhost:8000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static files & templates ---
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# --- API routers ---
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
app.include_router(messages.router, prefix="/rooms", tags=["messages"])
app.include_router(translate.router, prefix="/translate", tags=["translate"])
app.include_router(transcripts.router, prefix="/transcripts", tags=["transcripts"])
app.include_router(credits.router, prefix="/credits", tags=["credits"])
app.include_router(ws.router, tags=["websocket"])
app.include_router(stripe_webhooks.router, tags=["stripe"])
app.include_router(stripe_checkout.router, prefix="/stripe", tags=["stripe"])
app.include_router(api_v1.router, prefix="/api/v1", tags=["developer-api"])
app.include_router(integrations_router, prefix="/integrations", tags=["integrations"])

# --- Pages (HTML) router — mounted last, no prefix, so / serves the landing page ---
app.include_router(pages.router, tags=["pages"])


@app.get("/health")
async def health():
    return {"status": "ok"}
