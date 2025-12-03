from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSON, UUID
from datetime import datetime
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK
from typing import Optional
from uuid import UUID as PyUUID


class ScheduledTask(Base, AsyncCRUDMixin):
    """
    Модель для хранения запланированных задач.
    
    Задачи выполняются один раз в определенное время (execute_at).
    После выполнения задача удаляется из базы.
    """
    __tablename__ = "scheduled_tasks"

    task_id: Mapped[uuidPK]
    
    # ID карточки (для удобного поиска и удаления задач по карточке)
    card_id: Mapped[Optional[PyUUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Путь к функции для импорта (например: "modules.notifications.send_card_reminder")
    function_path: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Аргументы функции в формате JSON
    # Пример: {"card_id": "uuid-string", "message_type": "reminder"}
    arguments: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    # Время выполнения задачи
    execute_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return f"<ScheduledTask(id={self.task_id}, execute_at='{self.execute_at}')>"
