from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum
from uuid import UUID as _UUID
from database.connection import Base
from database.annotated_types import intAutoPK


class MessageType(str, Enum):
    """Типы сообщений"""
    can_take = "can_take"
    ready_review = "ready_review"
    ready_post = "ready_post"


class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[intAutoPK]
    card_id: Mapped[_UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cards.card_id"), nullable=False)
    type: Mapped[MessageType] = mapped_column(nullable=False)

    # Связи
    card: Mapped["Card"] = relationship("Card", back_populates="messages")
