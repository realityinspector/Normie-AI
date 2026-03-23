import uuid
import json
import logging
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
from fastapi import HTTPException

logger = logging.getLogger("normalaizer")

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
        logger.warning("WebSocket auth failed: invalid token for room=%s", room_id)
        await websocket.close(code=4001, reason="Unauthorized")
        return

    async with async_session() as db:
        # Verify user and room
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            logger.warning(
                "WebSocket auth failed: user not found user_id=%s room_id=%s",
                user_id,
                room_id,
            )
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
                    except HTTPException as exc:
                        if exc.status_code == 402:
                            logger.warning(
                                "Credit exhausted: user_id=%s room_id=%s",
                                user_id,
                                room_id,
                            )
                            await manager.send_to_user(
                                room_id,
                                user_id,
                                {
                                    "type": "error",
                                    "data": {
                                        "error_type": "credit_exhausted",
                                        "message": "You have used all your free credits. Upgrade to continue chatting.",
                                    },
                                },
                            )
                        else:
                            logger.error(
                                "Credit check error: user_id=%s room_id=%s status=%s detail=%s",
                                user_id,
                                room_id,
                                exc.status_code,
                                exc.detail,
                            )
                            await manager.send_to_user(
                                room_id,
                                user_id,
                                {
                                    "type": "error",
                                    "data": {
                                        "error_type": "server_error",
                                        "message": "Something went wrong. Please try again.",
                                    },
                                },
                            )
                        continue
                    except Exception:
                        logger.exception(
                            "Unexpected error during credit check: user_id=%s room_id=%s",
                            user_id,
                            room_id,
                        )
                        await manager.send_to_user(
                            room_id,
                            user_id,
                            {
                                "type": "error",
                                "data": {
                                    "error_type": "server_error",
                                    "message": "Something went wrong. Please try again.",
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
                                logger.error(
                                    "Translation failed: user_id=%s room_id=%s recipient_id=%s",
                                    user_id,
                                    room_id,
                                    rp.user_id,
                                    exc_info=True,
                                )
                                translations[str(rp.user_id)] = text
                                # Notify sender that translation failed
                                await manager.send_to_user(
                                    room_id,
                                    user_id,
                                    {
                                        "type": "error",
                                        "data": {
                                            "error_type": "translation_failed",
                                            "message": "Translation temporarily unavailable. Your message was sent as-is.",
                                        },
                                    },
                                )
                        else:
                            translations[str(rp.user_id)] = text

                    # Store message
                    try:
                        msg = Message(
                            room_id=room_id,
                            sender_id=user_id,
                            original_text=text,
                            translations=translations,
                        )
                        db.add(msg)
                        await db.commit()
                        await db.refresh(msg)
                    except Exception:
                        logger.exception(
                            "Database error saving message: user_id=%s room_id=%s",
                            user_id,
                            room_id,
                        )
                        await manager.send_to_user(
                            room_id,
                            user_id,
                            {
                                "type": "error",
                                "data": {
                                    "error_type": "server_error",
                                    "message": "Something went wrong. Please try again.",
                                },
                            },
                        )
                        continue

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
        logger.info(
            "WebSocket disconnected normally: user_id=%s room_id=%s",
            user_id,
            room_id,
        )
    except Exception:
        logger.exception(
            "WebSocket unexpected error: user_id=%s room_id=%s",
            user_id,
            room_id,
        )
        # Send error message to client before closing
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "data": {
                        "error_type": "server_error",
                        "message": "Connection lost, please refresh",
                    },
                }
            )
        except Exception:
            pass  # Client may already be disconnected
    finally:
        manager.disconnect(room_id, user_id)
        # Notify room of leave
        for uid in manager.get_room_connections(room_id):
            try:
                await manager.send_to_user(
                    room_id,
                    uid,
                    {
                        "type": "user_left",
                        "data": {"user_id": str(user_id)},
                    },
                )
            except Exception:
                logger.warning(
                    "Failed to send user_left notification: target_user=%s room_id=%s",
                    uid,
                    room_id,
                )
