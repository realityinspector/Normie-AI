from fastapi import APIRouter, Depends, UploadFile, File, Form
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

    translated = await translate_text(
        body.text, sender_style, recipient_style, body.template, body.custom_prompt
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

    extracted, translated = await extract_and_translate_image(
        image_bytes, media_type, sender_style, recipient_style, template
    )

    return TranslateImageResponse(
        extracted_text=extracted,
        translated_text=translated,
        direction=direction,
        credits_remaining=user.credit_balance,
    )
