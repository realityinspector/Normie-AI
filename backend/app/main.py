import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import auth, users, rooms, messages, translate, transcripts, credits, ws, api_v1
from app.routers.integrations import router as integrations_router

# Resolve paths relative to this file
_APP_DIR = pathlib.Path(__file__).resolve().parent
_STATIC_DIR = _APP_DIR / "static"
_TEMPLATES_DIR = _APP_DIR / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="NORMALIZER API",
    description="Cultural communication translation API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
app.include_router(api_v1.router, prefix="/api/v1", tags=["developer-api"])
app.include_router(integrations_router, prefix="/integrations", tags=["integrations"])


@app.get("/health")
async def health():
    return {"status": "ok"}
