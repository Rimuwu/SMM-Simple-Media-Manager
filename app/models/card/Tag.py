from sqlalchemy import String, Integer, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from models.card.Card import card_tags

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.card.Card import Card

class Tag(Base, AsyncCRUDMixin):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String, nullable=False)
    tag: Mapped[str] = mapped_column(String, nullable=False)

    forward_to_topic: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, default=None)

    order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)

    cards: Mapped[list["Card"]] = relationship(
        "Card", secondary=card_tags, back_populates="tags", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Tag(name='{self.name}', tag='{self.tag}')>"

    @classmethod
    async def create_tag(
        cls
    ): pass

    @classmethod
    async def update_name(
        cls
    ): pass

    @classmethod
    async def update_forward_topic(
        cls
    ): pass

    @classmethod
    async def update_order(
        cls
    ): pass

    @classmethod
    async def delete_tag(
        cls
    ): pass

    @classmethod
    async def get_sort_tags(
        cls
    ): pass