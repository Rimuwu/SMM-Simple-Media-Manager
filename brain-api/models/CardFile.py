from typing import Optional, TYPE_CHECKING
from uuid import UUID as _UUID
from sqlalchemy import String, BigInteger, ForeignKey, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK, createAT, updateAT

if TYPE_CHECKING:
    from models.Card import Card
    from sqlalchemy.ext.asyncio import AsyncSession


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
    
    # Скрытие файла (не отображается в списках)
    hide: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Временные метки
    created_at: Mapped[createAT]
    updated_at: Mapped[updateAT]

    # Relationship
    card: Mapped["Card"] = relationship("Card", back_populates="files", foreign_keys=[card_id])

    async def delete(self, session: Optional["AsyncSession"] = None) -> None:
        """При удалении из БД — пытаемся удалить файл в storage-api, затем удаляем запись в БД."""
        try:
            from modules.api_client import storage_api
            await storage_api.delete(f'/delete/{self.filename}')
        except Exception as e:
            from global_modules.logs import Logger
            Logger().get_logger("storage").warning(f"Failed to delete file {self.filename} from storage: {e}")
        finally:
            await super().delete(session=session)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "card_id": str(self.card_id),
            "filename": self.filename,
            "original_filename": self.original_filename,
            "size": self.size,
            "data_info": self.data_info,
            "order": self.order,
            "hide": self.hide,
            "created_at": getattr(self, 'created_at', None)
        }

    def __repr__(self) -> str:
        return f"<CardFile(id={self.id}, filename='{self.filename}', original='{self.original_filename}')>"
