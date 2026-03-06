from typing import Optional, TYPE_CHECKING
from datetime import datetime
from uuid import UUID as _UUID
from sqlalchemy import Text, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK, createAT

if TYPE_CHECKING:
    from models.Card import Card

class CardContent(Base, AsyncCRUDMixin):
    __tablename__ = "card_contents"

    id: Mapped[uuidPK]
    card_id: Mapped[_UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cards.card_id", ondelete="CASCADE"), nullable=False)
    client_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default={})

    created_at: Mapped[createAT]

    # Relationship
    card: Mapped["Card"] = relationship("Card", back_populates="contents")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "card_id": str(self.card_id),
            "client_key": self.client_key,
            "text": self.text,
            "meta": self.meta,
            "created_at": getattr(self, 'created_at', None)
        }
