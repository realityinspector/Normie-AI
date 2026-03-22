import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.room import Room, RoomParticipant
from app.schemas.room import RoomCreate, RoomRead, ParticipantRead

router = APIRouter()


def _room_to_read(room: Room) -> RoomRead:
    participants = []
    for rp in room.participants:
        if rp.user:
            participants.append(
                ParticipantRead(
                    id=rp.user.id,
                    display_name=rp.user.display_name,
                    communication_style=rp.user.communication_style,
                )
            )
    return RoomRead(
        id=room.id,
        name=room.name,
        is_public=room.is_public,
        owner_id=room.owner_id,
        participants=participants,
        created_at=room.created_at,
    )


@router.get("", response_model=list[RoomRead])
async def list_rooms(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Room)
        .join(RoomParticipant)
        .where(RoomParticipant.user_id == user.id)
        .options(selectinload(Room.participants).selectinload(RoomParticipant.user))
    )
    rooms = result.scalars().unique().all()
    return [_room_to_read(r) for r in rooms]


@router.get("/public", response_model=list[RoomRead])
async def list_public_rooms(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List public rooms that the current user has NOT yet joined."""
    # Subquery: room IDs the user is already a participant of
    user_room_ids = (
        select(RoomParticipant.room_id)
        .where(RoomParticipant.user_id == user.id)
        .scalar_subquery()
    )
    result = await db.execute(
        select(Room)
        .where(Room.is_public == True, Room.id.notin_(user_room_ids))  # noqa: E712
        .options(selectinload(Room.participants).selectinload(RoomParticipant.user))
        .order_by(Room.created_at.desc())
        .limit(50)
    )
    rooms = result.scalars().unique().all()
    return [_room_to_read(r) for r in rooms]


@router.post("", response_model=RoomRead, status_code=status.HTTP_201_CREATED)
async def create_room(
    body: RoomCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    room = Room(name=body.name, is_public=body.is_public, owner_id=user.id)
    db.add(room)
    await db.flush()

    participant = RoomParticipant(room_id=room.id, user_id=user.id)
    db.add(participant)
    await db.flush()

    # Reload with relationships
    result = await db.execute(
        select(Room)
        .where(Room.id == room.id)
        .options(selectinload(Room.participants).selectinload(RoomParticipant.user))
    )
    room = result.scalar_one()
    return _room_to_read(room)


@router.get("/{room_id}", response_model=RoomRead)
async def get_room(
    room_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Room)
        .where(Room.id == room_id)
        .options(selectinload(Room.participants).selectinload(RoomParticipant.user))
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Check access
    participant_ids = [rp.user_id for rp in room.participants]
    if not room.is_public and user.id not in participant_ids:
        raise HTTPException(status_code=403, detail="Not a participant")

    return _room_to_read(room)


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.owner_id != user.id:
        raise HTTPException(
            status_code=403, detail="Only the owner can delete this room"
        )
    await db.delete(room)


@router.post("/{room_id}/join", response_model=RoomRead)
async def join_room(
    room_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Room)
        .where(Room.id == room_id)
        .options(selectinload(Room.participants).selectinload(RoomParticipant.user))
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if not room.is_public:
        raise HTTPException(status_code=403, detail="Cannot join a private room")

    participant_ids = [rp.user_id for rp in room.participants]
    if user.id not in participant_ids:
        db.add(RoomParticipant(room_id=room.id, user_id=user.id))
        try:
            await db.flush()
        except IntegrityError:
            # User already joined concurrently — idempotent, just reload
            await db.rollback()

        # Reload
        result = await db.execute(
            select(Room)
            .where(Room.id == room.id)
            .options(selectinload(Room.participants).selectinload(RoomParticipant.user))
        )
        room = result.scalar_one()

    return _room_to_read(room)
