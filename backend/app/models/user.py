import uuid
import string
import secrets
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
import enum


def _generate_referral_code() -> str:
    """Generate a unique 8-character alphanumeric referral code."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


class CommunicationStyle(str, enum.Enum):
    neurotypical = "neurotypical"
    autistic = "autistic"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    apple_sub: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), default="User")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    communication_style: Mapped[CommunicationStyle] = mapped_column(
        SAEnum(CommunicationStyle), default=CommunicationStyle.neurotypical
    )
    credit_balance: Mapped[int] = mapped_column(Integer, default=50)
    subscription_active: Mapped[bool] = mapped_column(Boolean, default=False)
    subscription_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    referral_code: Mapped[str] = mapped_column(
        String(8), unique=True, index=True, default=_generate_referral_code
    )
    referred_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
