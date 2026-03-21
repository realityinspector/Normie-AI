import uuid
from datetime import datetime
from pydantic import BaseModel


class MessageRead(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    sender_id: uuid.UUID
    sender_name: str
    original_text: str
    translated_text: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
