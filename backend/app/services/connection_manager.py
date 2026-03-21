import uuid
import json
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections organized by room."""

    def __init__(self):
        # room_id -> {user_id -> WebSocket}
        self.rooms: dict[uuid.UUID, dict[uuid.UUID, WebSocket]] = {}

    async def connect(self, room_id: uuid.UUID, user_id: uuid.UUID, ws: WebSocket):
        await ws.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = {}
        self.rooms[room_id][user_id] = ws

    def disconnect(self, room_id: uuid.UUID, user_id: uuid.UUID):
        if room_id in self.rooms:
            self.rooms[room_id].pop(user_id, None)
            if not self.rooms[room_id]:
                del self.rooms[room_id]

    def get_room_connections(self, room_id: uuid.UUID) -> dict[uuid.UUID, WebSocket]:
        return self.rooms.get(room_id, {})

    async def send_to_user(self, room_id: uuid.UUID, user_id: uuid.UUID, data: dict):
        connections = self.rooms.get(room_id, {})
        ws = connections.get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                self.disconnect(room_id, user_id)


manager = ConnectionManager()
