import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User, CommunicationStyle
from app.models.room import Room
from app.models.message import Message
from app.schemas.message import MessageRead
from app.services.claude_translate import translate_text

router = APIRouter()
logger = logging.getLogger("normalaizer")


@router.get("/{room_id}/messages", response_model=list[MessageRead])
async def get_messages(
    room_id: uuid.UUID,
    before: datetime | None = Query(None),
    limit: int = Query(50, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify room access
    result = await db.execute(
        select(Room)
        .where(Room.id == room_id)
        .options(selectinload(Room.participants))
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    participant_ids = [rp.user_id for rp in room.participants]
    if not room.is_public and user.id not in participant_ids:
        raise HTTPException(status_code=403, detail="Not a participant")

    # Fetch messages + sender so we can translate on demand if needed.
    query = select(Message).where(Message.room_id == room_id)
    if before:
        query = query.where(Message.created_at < before)
    query = query.order_by(Message.created_at.desc()).limit(limit)

    result = await db.execute(query.options(selectinload(Message.sender)))
    messages = result.scalars().all()

    # Build response with personalized translations. For messages sent before
    # this user joined (or before anyone with their style joined), the cached
    # translations dict won't have an entry for them — translate on demand
    # and cache the result back into msg.translations so we only pay once.
    response = []
    dirty = False
    for msg in reversed(messages):
        translations = msg.translations or {}
        translated = translations.get(str(user.id))
        if (
            translated is None
            and msg.sender_id != user.id
            and msg.sender is not None
            and msg.sender.communication_style != user.communication_style
            and user.communication_style in (
                CommunicationStyle.autistic,
                CommunicationStyle.neurotypical,
            )
        ):
            try:
                translated = await translate_text(
                    msg.original_text,
                    msg.sender.communication_style,
                    user.communication_style,
                )
                translations[str(user.id)] = translated
                msg.translations = translations
                flag_modified(msg, "translations")
                dirty = True
            except Exception:
                logger.exception(
                    "On-demand translation failed: msg_id=%s viewer_id=%s",
                    msg.id,
                    user.id,
                )

        response.append(
            MessageRead(
                id=msg.id,
                room_id=msg.room_id,
                sender_id=msg.sender_id,
                sender_name=msg.sender.display_name if msg.sender else "Unknown",
                original_text=msg.original_text
                if msg.sender_id == user.id
                else (translated or msg.original_text),
                translated_text=translated if msg.sender_id != user.id else None,
                created_at=msg.created_at,
            )
        )

    if dirty:
        try:
            await db.commit()
        except Exception:
            logger.exception("Failed to persist on-demand translations")
            await db.rollback()

    return response
