import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.message import Message
from app.models.room import Room
from app.models.transcript import Transcript
from app.schemas.transcript import TranscriptRead, TranscriptCreate, TranscriptDetailRead
from app.schemas.message import MessageRead

router = APIRouter()


@router.get("", response_model=list[TranscriptRead])
async def list_transcripts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transcript)
        .where(Transcript.user_id == user.id)
        .order_by(Transcript.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=TranscriptRead, status_code=201)
async def create_transcript(
    body: TranscriptCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify room exists
    result = await db.execute(select(Room).where(Room.id == body.room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Count messages
    count_result = await db.execute(
        select(func.count()).select_from(Message).where(Message.room_id == body.room_id)
    )
    msg_count = count_result.scalar()

    transcript = Transcript(
        user_id=user.id,
        room_id=body.room_id,
        room_name=room.name,
        message_count=msg_count,
    )
    db.add(transcript)
    await db.flush()
    return transcript


@router.get("/{transcript_id}", response_model=TranscriptDetailRead)
async def get_transcript(
    transcript_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transcript).where(Transcript.id == transcript_id)
    )
    transcript = result.scalar_one_or_none()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    if transcript.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your transcript")

    # Get messages
    msg_result = await db.execute(
        select(Message)
        .where(Message.room_id == transcript.room_id)
        .order_by(Message.created_at.asc())
        .options(selectinload(Message.sender))
    )
    messages = msg_result.scalars().all()

    msg_reads = []
    for msg in messages:
        translated = msg.translations.get(str(user.id)) if msg.translations else None
        msg_reads.append(
            MessageRead(
                id=msg.id,
                room_id=msg.room_id,
                sender_id=msg.sender_id,
                sender_name=msg.sender.display_name if msg.sender else "Unknown",
                original_text=msg.original_text,
                translated_text=translated,
                created_at=msg.created_at,
            )
        )

    return TranscriptDetailRead(
        transcript=TranscriptRead.model_validate(transcript),
        messages=msg_reads,
    )


@router.get("/public/{slug}", response_model=TranscriptDetailRead)
async def get_public_transcript(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Transcript).where(Transcript.slug == slug))
    transcript = result.scalar_one_or_none()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    msg_result = await db.execute(
        select(Message)
        .where(Message.room_id == transcript.room_id)
        .order_by(Message.created_at.asc())
        .options(selectinload(Message.sender))
    )
    messages = msg_result.scalars().all()

    msg_reads = []
    for msg in messages:
        msg_reads.append(
            MessageRead(
                id=msg.id,
                room_id=msg.room_id,
                sender_id=msg.sender_id,
                sender_name=msg.sender.display_name if msg.sender else "Unknown",
                original_text=msg.original_text,
                translated_text=None,  # Public view doesn't show translations
                created_at=msg.created_at,
            )
        )

    return TranscriptDetailRead(
        transcript=TranscriptRead.model_validate(transcript),
        messages=msg_reads,
    )
