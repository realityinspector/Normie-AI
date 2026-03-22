import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import get_current_user
from app.middleware.api_key import get_api_key_user
from app.models.api_key import ApiKey
from app.models.user import User, CommunicationStyle
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyListItem,
    ApiTranslateRequest,
    ApiTranslateResponse,
    ApiKeyUsageResponse,
)
from app.schemas.translate import TranslationDirection
from app.services.claude_translate import translate_text

router = APIRouter()


# ── API Key CRUD (JWT-authenticated) ──────────────────────────────────


@router.post("/keys", response_model=ApiKeyResponse, tags=["api-keys"])
async def create_api_key(
    body: ApiKeyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key for the authenticated user."""
    api_key = ApiKey(
        user_id=user.id,
        name=body.name,
        rate_limit=body.rate_limit,
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)
    return api_key


@router.get("/keys", response_model=list[ApiKeyListItem], tags=["api-keys"])
async def list_api_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for the authenticated user (keys are masked)."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        ApiKeyListItem(
            id=k.id,
            name=k.name,
            key_prefix=k.key[:12] + "...",
            rate_limit=k.rate_limit,
            created_at=k.created_at,
            is_active=k.is_active,
            request_count=k.request_count,
            last_used_at=k.last_used_at,
        )
        for k in keys
    ]


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["api-keys"])
async def revoke_api_key(
    key_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke (deactivate) an API key."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    api_key.is_active = False
    db.add(api_key)
    await db.flush()


# ── Developer API endpoints (API-key-authenticated) ──────────────────


def _direction_to_styles(direction: str) -> tuple[CommunicationStyle, CommunicationStyle]:
    """Convert direction string to sender/recipient communication styles."""
    try:
        dir_enum = TranslationDirection(direction)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid direction. Must be one of: {', '.join(d.value for d in TranslationDirection)}",
        )
    if dir_enum == TranslationDirection.autistic_to_neurotypical:
        return CommunicationStyle.autistic, CommunicationStyle.neurotypical
    return CommunicationStyle.neurotypical, CommunicationStyle.autistic


@router.post("/translate", response_model=ApiTranslateResponse, tags=["developer-api"])
async def api_translate(
    body: ApiTranslateRequest,
    user: User = Depends(get_api_key_user),
    db: AsyncSession = Depends(get_db),
):
    """Translate text between communication styles. Requires a valid API key via X-API-Key header."""
    sender_style, recipient_style = _direction_to_styles(body.direction)

    translated = await translate_text(
        body.text, sender_style, recipient_style, body.template
    )

    return ApiTranslateResponse(
        original_text=body.text,
        translated_text=translated,
        direction=body.direction,
    )


@router.get("/usage", response_model=list[ApiKeyUsageResponse], tags=["developer-api"])
async def api_usage(
    user: User = Depends(get_api_key_user),
    db: AsyncSession = Depends(get_db),
):
    """Get usage statistics for all API keys owned by the authenticated user."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        ApiKeyUsageResponse(
            api_key_id=k.id,
            api_key_name=k.name,
            request_count=k.request_count,
            rate_limit=k.rate_limit,
            last_used_at=k.last_used_at,
        )
        for k in keys
    ]
