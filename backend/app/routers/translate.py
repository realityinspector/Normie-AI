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

logger = logging.getLogger(__name__)

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
        logger.error("Translation failed for user %s: %s", user.id, str(exc))
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
    await check_access(db, user)
    sender_style, recipient_style = _direction_to_styles(direction)

    image_bytes = await image.read()
    media_type = image.content_type or "image/jpeg"

    try:
        extracted, translated = await extract_and_translate_image(
            image_bytes, media_type, sender_style, recipient_style, template
        )
    except Exception as exc:
        logger.error("Image translation failed for user %s: %s", user.id, str(exc))
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
