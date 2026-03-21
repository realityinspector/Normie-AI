import uuid
from datetime import datetime
from pydantic import BaseModel
from app.schemas.message import MessageRead


class TranscriptRead(BaseModel):
    id: uuid.UUID
    room_name: str
    message_count: int
    slug: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TranscriptCreate(BaseModel):
    room_id: uuid.UUID


class TranscriptDetailRead(BaseModel):
    transcript: TranscriptRead
    messages: list[MessageRead]
