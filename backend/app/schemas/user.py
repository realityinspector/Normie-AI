import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.user import CommunicationStyle


class UserRead(BaseModel):
    id: uuid.UUID
    display_name: str
    email: str | None
    communication_style: CommunicationStyle
    credit_balance: int
    subscription_active: bool
    subscription_expires_at: datetime | None
    referral_code: str
    referred_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    display_name: str | None = None
    communication_style: CommunicationStyle | None = None
