import uuid
import secrets
import string
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def _generate_slug() -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(8))


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id"))
    room_name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(16), unique=True, index=True, default=_generate_slug)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
