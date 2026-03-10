from typing import Optional, TYPE_CHECKING
from uuid import UUID as _UUID
from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK

if TYPE_CHECKING:
    from app.models.card.Card import Card


class ClientEntity(Base, AsyncCRUDMixin):
    __tablename__ = "client_entities"
    __table_args__ = (
        UniqueConstraint("type", "client_key", "card_id", name="uq_entity_type_client_card"),
    )

    id: Mapped[uuidPK]
    card_id: Mapped[_UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
    )

    client_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    type: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationship
    card: Mapped["Card"] = relationship("Card", back_populates="entities_entries", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ClientEntity(id='{self.id}', card_id='{self.card_id}', client_key='{self.client_key}', type='{self.type}')>"

    @classmethod
    async def create_entity(
        cls
    ): pass


    @classmethod
    async def create_tg_poll(
        cls
    ): pass

    async def send_poll(
        self
    ): pass


    @classmethod
    async def create_tg_inline_line(
        cls
    ): pass

    async def send_inline_line(
        self
    ): pass
