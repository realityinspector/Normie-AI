import uuid
from datetime import datetime
from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    name: str
    rate_limit: int = 100


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key: str
    rate_limit: int
    created_at: datetime
    is_active: bool
    request_count: int
    last_used_at: datetime | None

    model_config = {"from_attributes": True}


class ApiKeyListItem(BaseModel):
    """Like ApiKeyResponse but masks the key for security."""
    id: uuid.UUID
    name: str
    key_prefix: str  # Only first 12 chars shown
    rate_limit: int
    created_at: datetime
    is_active: bool
    request_count: int
    last_used_at: datetime | None


class ApiKeyUsageResponse(BaseModel):
    api_key_id: uuid.UUID
    api_key_name: str
    request_count: int
    rate_limit: int
    last_used_at: datetime | None


class ApiTranslateRequest(BaseModel):
    text: str
    direction: str  # "autistic_to_neurotypical" or "neurotypical_to_autistic"
    template: str | None = None


class ApiTranslateResponse(BaseModel):
    original_text: str
    translated_text: str
    direction: str
