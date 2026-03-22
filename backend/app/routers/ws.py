import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import jwt as pyjwt
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.config import get_settings
from app.database import async_session
from app.models.user import User, CommunicationStyle
from app.models.room import Room, RoomParticipant
from app.models.message import Message
from app.services.claude_translate import translate_text
from app.services.credit_manager import check_and_deduct
from app.services.connection_manager import manager

router = APIRouter()


async def _authenticate_ws(token: str) -> uuid.UUID | None:
    """Verify JWT from WebSocket query param and return user_id."""
    settings = get_settings()
    try:
        payload = pyjwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return uuid.UUID(payload["sub"])
    except Exception:
        return None


@router.websocket("/ws/rooms/{room_id}")
async def chat_websocket(
    websocket: WebSocket,
    room_id: uuid.UUID,
    token: str = Query(...),
):
    user_id = await _authenticate_ws(token)
    if not user_id:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    async with async_session() as db:
        # Verify user and room
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            await websocket.close(code=4001, reason="User not found")
            return

        room_result = await db.execute(
            select(Room)
            .where(Room.id == room_id)
            .options(selectinload(Room.participants).selectinload(RoomParticipant.user))
        )
        room = room_result.scalar_one_or_none()
        if not room:
            await websocket.close(code=4004, reason="Room not found")
            return

        participant_ids = [rp.user_id for rp in room.participants]
        if not room.is_public and user_id not in participant_ids:
            await websocket.close(code=4003, reason="Not a participant")
            return

    await manager.connect(room_id, user_id, websocket)

    # Notify room of join
    connections = manager.get_room_connections(room_id)
    for uid in connections:
        if uid != user_id:
            await manager.send_to_user(
                room_id,
                uid,
                {
                    "type": "user_joined",
                    "data": {
                        "user_id": str(user_id),
                        "display_name": user.display_name,
                    },
                },
            )

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "send_message":
                text = data.get("text", "").strip()
                if not text:
                    continue

                async with async_session() as db:
                    try:
                        # Atomically check access and deduct credits in one step
                        user_result2 = await db.execute(
                            select(User).where(User.id == user_id)
                        )
                        current_user = user_result2.scalar_one()

                        # Neurodivergent users: always free
                        is_neurodivergent = (
                            current_user.communication_style
                            == CommunicationStyle.autistic
                        )
                        # Active subscription: unlimited access
                        has_subscription = (
                            current_user.subscription_active
                            and current_user.subscription_expires_at is not None
                            and current_user.subscription_expires_at
                            > datetime.now(timezone.utc)
                        )

                        if not is_neurodivergent and not has_subscription:
                            # Atomic check-and-deduct: no separate check_access
                            # This prevents the race between checking balance
                            # and deducting credits
                            await check_and_deduct(
                                db,
                                current_user.id,
                                1,
                                "Chat message credit usage",
                            )
                    except Exception:
                        await manager.send_to_user(
                            room_id,
                            user_id,
                            {
                                "type": "error",
                                "data": {
                                    "message": "Subscription required. Neurodivergent users get free access."
                                },
                            },
                        )
                        continue

                    # Reload room participants
                    room_result = await db.execute(
                        select(Room)
                        .where(Room.id == room_id)
                        .options(
                            selectinload(Room.participants).selectinload(
                                RoomParticipant.user
                            )
                        )
                    )
                    room = room_result.scalar_one()

                    # Translate for each participant with different style
                    translations = {}
                    for rp in room.participants:
                        if rp.user_id == user_id:
                            continue
                        recipient = rp.user
                        if not recipient:
                            continue
                        if user.communication_style != recipient.communication_style:
                            try:
                                translated = await translate_text(
                                    text,
                                    user.communication_style,
                                    recipient.communication_style,
                                )
                                translations[str(rp.user_id)] = translated
                            except Exception:
                                translations[str(rp.user_id)] = text
                        else:
                            translations[str(rp.user_id)] = text

                    # Store message
                    msg = Message(
                        room_id=room_id,
                        sender_id=user_id,
                        original_text=text,
                        translations=translations,
                    )
                    db.add(msg)
                    await db.commit()
                    await db.refresh(msg)

                    # Broadcast to all connections
                    now = msg.created_at.isoformat()
                    for uid, ws in manager.get_room_connections(room_id).items():
                        if uid == user_id:
                            # Sender sees original
                            await manager.send_to_user(
                                room_id,
                                uid,
                                {
                                    "type": "message",
                                    "data": {
                                        "id": str(msg.id),
                                        "sender_id": str(user_id),
                                        "sender_name": user.display_name,
                                        "original_text": text,
                                        "translated_text": None,
                                        "created_at": now,
                                    },
                                },
                            )
                        else:
                            # Recipient sees translated version
                            translated = translations.get(str(uid), text)
                            await manager.send_to_user(
                                room_id,
                                uid,
                                {
                                    "type": "message",
                                    "data": {
                                        "id": str(msg.id),
                                        "sender_id": str(user_id),
                                        "sender_name": user.display_name,
                                        "original_text": translated,
                                        "translated_text": translated,
                                        "created_at": now,
                                    },
                                },
                            )

    except WebSocketDisconnect:
        manager.disconnect(room_id, user_id)
        # Notify room of leave
        for uid in manager.get_room_connections(room_id):
            await manager.send_to_user(
                room_id,
                uid,
                {
                    "type": "user_left",
                    "data": {"user_id": str(user_id)},
                },
            )
    except Exception:
        manager.disconnect(room_id, user_id)
