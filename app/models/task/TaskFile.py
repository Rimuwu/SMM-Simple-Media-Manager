from typing import Optional, TYPE_CHECKING
from uuid import UUID as _UUID
from sqlalchemy import String, BigInteger, ForeignKey, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK, createAT, updateAT

if TYPE_CHECKING:
    from app.models.task.Task import Task
    from sqlalchemy.ext.asyncio import AsyncSession


class TaskFile(Base, AsyncCRUDMixin):
    __tablename__ = "task_files"

    id: Mapped[uuidPK]
    task_id: Mapped[_UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)

    # Имя файла в хранилище (UUID + расширение)
    filename: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    # Размер файла в байтах
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Метаданные (тип файла, описание и т.д.)
    data_info: Mapped[dict] = mapped_column(JSON, nullable=False, default={})

    # Временные метки
    created_at: Mapped[createAT]
    updated_at: Mapped[updateAT]

    # Relationship
    task: Mapped["Task"] = relationship(
        "Task", back_populates="files", foreign_keys=[task_id], lazy="selectin")

    async def delete(self, session: Optional["AsyncSession"] = None) -> None:
        """При удалении из БД — удаляем файл из локального хранилища, затем запись в БД."""
        try:
            from app.modules.components.storage import delete_file
            await delete_file(self.filename)

        except Exception as e:
            from app.modules.components.logs import Logger
            Logger().get_logger("storage"
                                ).warning(f"Failed to delete file {self.filename} from storage: {e}")
        finally:
            await super().delete(session=session)

    def __repr__(self) -> str:
        return f"<TaskFile(id={self.id}, filename='{self.filename}', original='{self.original_filename}')>"

    @classmethod
    async def create_file(
        cls
    ): pass

    @classmethod
    async def upload(
        cls,
        task_id: str,
        file_data: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> Optional["TaskFile"]:
        """Загрузить файл в хранилище и создать запись в БД."""

        from app.modules.components.storage import upload_file as _up

        result = await _up(file_data, filename, content_type)
        if result.get("status") != "success":
            return None

        return await cls.create(
            task_id=_UUID(str(task_id)),
            filename=result["filename"],
            original_filename=filename,
            size=len(file_data),
            data_info={"content_type": content_type or ""}
        )
