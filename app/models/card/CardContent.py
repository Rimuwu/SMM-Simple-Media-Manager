from typing import Optional, TYPE_CHECKING
from uuid import UUID as _UUID
from sqlalchemy import Text, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK, createAT

if TYPE_CHECKING:
    from app.models.card.Card import Card


class CardContent(Base, AsyncCRUDMixin):
    __tablename__ = "card_contents"

    id: Mapped[uuidPK]
    card_id: Mapped[_UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), 
        nullable=False
    )

    client_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default={})

    created_at: Mapped[createAT]


    card: Mapped["Card"] = relationship("Card", back_populates="contents", lazy="selectin")

    def __repr__(self) -> str:
        return f"<CardContent(id='{self.id}', card_id='{self.card_id}', client_key='{self.client_key}')>"

    @classmethod
    async def create_client_content(cls
    ): pass

    async def edit_content(
        self
    ): pass

    async def delete_content(
        self
    ): pass