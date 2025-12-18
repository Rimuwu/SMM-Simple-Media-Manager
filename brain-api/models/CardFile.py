from typing import Optional, TYPE_CHECKING
from uuid import UUID as _UUID
from sqlalchemy import String, BigInteger, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK, createAT, updateAT

if TYPE_CHECKING:
    from models.Card import Card


class CardFile(Base, AsyncCRUDMixin):
    __tablename__ = "card_files"

    id: Mapped[uuidPK]
    card_id: Mapped[_UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cards.card_id", ondelete="CASCADE"), nullable=False)
    
    # Имя файла в хранилище (UUID + расширение)
    filename: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    
    # Оригинальное имя файла
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    
    # Размер файла в байтах
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    # Метаданные (тип файла, описание и т.д.)
    data_info: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    
    # Порядок файла в списке отправки (для сортировки)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Временные метки
    created_at: Mapped[createAT]
    updated_at: Mapped[updateAT]

    # Relationship - используем только ForeignKey, без back_populates
    card: Mapped["Card"] = relationship("Card", foreign_keys=[card_id], viewonly=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "card_id": str(self.card_id),
            "filename": self.filename,
            "original_filename": self.original_filename,
            "size": self.size,
            "data_info": self.data_info,
            "order": self.order,
            "created_at": getattr(self, 'created_at', None)
        }

    def __repr__(self) -> str:
        return f"<CardFile(id={self.id}, filename='{self.filename}', original='{self.original_filename}')>"
