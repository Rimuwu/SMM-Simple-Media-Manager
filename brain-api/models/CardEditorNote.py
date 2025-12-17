from typing import Optional, TYPE_CHECKING
from datetime import datetime
from uuid import UUID as _UUID
from sqlalchemy import Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK, createAT

if TYPE_CHECKING:
    from models.Card import Card

class CardEditorNote(Base, AsyncCRUDMixin):
    __tablename__ = "card_editor_notes"

    id: Mapped[uuidPK]
    card_id: Mapped[_UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    author: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=False)

    created_at: Mapped[createAT]

    # Relationship
    card: Mapped["Card"] = relationship("Card", back_populates="editor_notes_entries")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "card_id": str(self.card_id),
            "author": self.author,
            "content": self.content,
            "created_at": getattr(self, 'created_at', None)
        }
