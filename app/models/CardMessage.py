from typing import Optional, TYPE_CHECKING
from uuid import UUID as _UUID
from sqlalchemy import String, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK, createAT, updateAT

if TYPE_CHECKING:
    from models.Card import Card


class CardMessage(Base, AsyncCRUDMixin):
    """
    Модель для хранения информации о сообщениях, связанных с карточкой.
    Может хранить ID форум-сообщений, превью-сообщений и других типов сообщений.
    """
    __tablename__ = "card_messages"

    id: Mapped[uuidPK]
    card_id: Mapped[_UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cards.card_id", ondelete="CASCADE"), nullable=False)
    
    # Тип сообщения: 'forum', 'complete_preview', и т.д.
    message_type: Mapped[str] = mapped_column(String, nullable=False)
    
    # ID сообщения в целевой системе (например, ID в форуме, ID в executor API)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    # Дополнительные данные (например, информация о клиенте для complete_preview)
    data_info: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Временные метки
    created_at: Mapped[createAT]
    updated_at: Mapped[updateAT]

    # Relationship
    card: Mapped["Card"] = relationship("Card", back_populates="messages", foreign_keys=[card_id])

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "card_id": str(self.card_id),
            "message_type": self.message_type,
            "message_id": self.message_id,
            "data_info": self.data_info,
            "created_at": getattr(self, 'created_at', None)
        }

    def __repr__(self) -> str:
        return f"<CardMessage(id={self.id}, type='{self.message_type}', message_id={self.message_id})>"
