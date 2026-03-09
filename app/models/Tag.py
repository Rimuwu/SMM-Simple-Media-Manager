from sqlalchemy import String, Integer, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin


class Tag(Base, AsyncCRUDMixin):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    tag: Mapped[str] = mapped_column(String, nullable=False)
    forward_to_topic: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, default=None)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<Tag(key='{self.key}', name='{self.name}')>"

    @classmethod
    async def all_sorted(cls) -> "list[Tag]":
        """Все теги, отсортированные по полю ``order``."""
        tags = await cls.get_all()
        return sorted(tags, key=lambda t: t.order)
