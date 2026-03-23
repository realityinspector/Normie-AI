import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User, CommunicationStyle
from app.schemas.translate import (
    TranslateTextRequest,
    TranslateTextResponse,
    TranslateImageResponse,
    TranslationDirection,
)
from app.services.claude_translate import translate_text, extract_and_translate_image
from app.services.credit_manager import check_access

logger = logging.getLogger("normalaizer")

# 10 MB max image size
MAX_IMAGE_SIZE = 10 * 1024 * 1024

router = APIRouter()


def _direction_to_styles(
    direction: TranslationDirection,
) -> tuple[CommunicationStyle, CommunicationStyle]:
    if direction == TranslationDirection.autistic_to_neurotypical:
        return CommunicationStyle.autistic, CommunicationStyle.neurotypical
    return CommunicationStyle.neurotypical, CommunicationStyle.autistic


@router.post("/text", response_model=TranslateTextResponse)
async def translate_text_endpoint(
    body: TranslateTextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await check_access(db, user)
    sender_style, recipient_style = _direction_to_styles(body.direction)

    try:
        translated = await translate_text(
            body.text, sender_style, recipient_style, body.template, body.custom_prompt
        )
    except Exception as exc:
        logger.error(
            "Translation failed: user_id=%s endpoint=translate_text error=%s",
            user.id,
            str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Translation service temporarily unavailable. Please try again.",
        )

    return TranslateTextResponse(
        original_text=body.text,
        translated_text=translated,
        direction=body.direction,
        credits_remaining=user.credit_balance,
    )


@router.post("/image", response_model=TranslateImageResponse)
async def translate_image_endpoint(
    image: UploadFile = File(...),
    direction: TranslationDirection = Form(...),
    template: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate content type
    content_type = image.content_type or ""
    if not content_type.startswith("image/"):
        logger.warning(
            "Image upload rejected: invalid content_type=%s user_id=%s",
            content_type,
            user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File must be an image (e.g., image/jpeg, image/png).",
        )

    await check_access(db, user)
    sender_style, recipient_style = _direction_to_styles(direction)

    image_bytes = await image.read()

    # Validate file size
    if len(image_bytes) > MAX_IMAGE_SIZE:
        logger.warning(
            "Image upload rejected: size=%d exceeds max=%d user_id=%s",
            len(image_bytes),
            MAX_IMAGE_SIZE,
            user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image file too large. Maximum size is 10MB.",
        )

    media_type = content_type or "image/jpeg"

    try:
        extracted, translated = await extract_and_translate_image(
            image_bytes, media_type, sender_style, recipient_style, template
        )
    except Exception as exc:
        logger.error(
            "Image translation failed: user_id=%s endpoint=translate_image error=%s",
            user.id,
            str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Translation service temporarily unavailable. Please try again.",
        )

    return TranslateImageResponse(
        extracted_text=extracted,
        translated_text=translated,
        direction=direction,
        credits_remaining=user.credit_balance,
    )
