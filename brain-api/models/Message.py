from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum
from uuid import UUID as _UUID
from database.connection import Base
from database.annotated_types import intAutoPK
from global_modules.classes.enums import MessageType


class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[intAutoPK]
    card_id: Mapped[_UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cards.card_id"), nullable=False)
    type: Mapped[MessageType] = mapped_column(nullable=False)

    # Связи
    card: Mapped["Card"] = relationship("Card", back_populates="messages")
