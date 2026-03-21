import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.user import CommunicationStyle


class RoomCreate(BaseModel):
    name: str
    is_public: bool = False


class ParticipantRead(BaseModel):
    id: uuid.UUID
    display_name: str
    communication_style: CommunicationStyle

    model_config = {"from_attributes": True}


class RoomRead(BaseModel):
    id: uuid.UUID
    name: str
    is_public: bool
    owner_id: uuid.UUID
    participants: list[ParticipantRead] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class RoomUpdate(BaseModel):
    name: str | None = None
    is_public: bool | None = None
