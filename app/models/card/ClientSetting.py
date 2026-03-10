from typing import Optional, TYPE_CHECKING
from uuid import UUID as _UUID
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK

if TYPE_CHECKING:
    from app.models.card.Card import Card


class ClientSetting(Base, AsyncCRUDMixin):
    __tablename__ = "client_settings"

    id: Mapped[uuidPK]
    card_id: Mapped[_UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False)

    client_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    data: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    type: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationship
    card: Mapped["Card"] = relationship(
        "Card", back_populates="clients_settings_entries", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ClientSetting(id='{self.id}', card_id='{self.card_id}', client_key='{self.client_key}', type='{self.type}')>"

    @classmethod
    async def create_setting(
        cls
    ): pass


    @classmethod
    async def create_vk_image_view(
        cls
    ): pass

    @classmethod
    async def create_tg_pin_message(
        cls
    ): pass

    @classmethod
    async def create_tg_forward_message(
        cls
    ): pass