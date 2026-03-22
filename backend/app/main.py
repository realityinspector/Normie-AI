from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, users, rooms, messages, translate, transcripts, credits, ws
from app.routers.integrations import router as integrations_router


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

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
app.include_router(messages.router, prefix="/rooms", tags=["messages"])
app.include_router(translate.router, prefix="/translate", tags=["translate"])
app.include_router(transcripts.router, prefix="/transcripts", tags=["transcripts"])
app.include_router(credits.router, prefix="/credits", tags=["credits"])
app.include_router(ws.router, tags=["websocket"])
app.include_router(integrations_router, prefix="/integrations", tags=["integrations"])


@app.get("/health")
async def health():
    return {"status": "ok"}
