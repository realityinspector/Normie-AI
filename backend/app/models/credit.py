import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class TransactionType(str, enum.Enum):
    purchase = "purchase"
    usage = "usage"
    bonus = "bonus"


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)  # positive=add, negative=deduct
    transaction_type: Mapped[TransactionType] = mapped_column(SAEnum(TransactionType))
    apple_transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
