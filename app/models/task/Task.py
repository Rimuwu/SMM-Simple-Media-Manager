from sqlalchemy import BigInteger, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID as _UUID
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK, createAT, updateAT

if TYPE_CHECKING:
    from models.User import User
    from app.models.card.Card import Card
    from app.models.task.TaskFile import TaskFile
    from app.models.Message import Message


class Task(Base, AsyncCRUDMixin):
    __tablename__ = "tasks"

    id: Mapped[uuidPK]

    # Название и тз
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Картинка
    image_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_count: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, default=1)

    # Заказчик задания
    customer_id: Mapped[Optional[_UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    customer: Mapped[Optional["User"]] = relationship(
        "User", back_populates="own_tasks", foreign_keys=[customer_id], lazy="selectin"
    )

    # Исполнитель задания
    executor_id: Mapped[Optional[_UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    executor: Mapped[Optional["User"]] = relationship(
        "User", back_populates="executed_tasks", foreign_keys=[executor_id], lazy="selectin"
    )

    # Редактор
    editor_id: Mapped[Optional[_UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    editor: Mapped[Optional["User"]] = relationship(
        "User", back_populates="edited_tasks", foreign_keys=[editor_id], lazy="selectin"
    )

    # Общий итоговый дедлайн
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Посты (карточки), привязанные к этому заданию
    cards: Mapped[List["Card"]] = relationship(
        "Card", back_populates="task", foreign_keys="Card.task_id", lazy="selectin"
    )

    # Файлы карточки
    files: Mapped[list["TaskFile"]] = relationship(
        "TaskFile", back_populates="task", cascade="all, delete-orphan", lazy="selectin")

    created_at: Mapped[createAT]
    updated_at: Mapped[updateAT]

    def __repr__(self) -> str:
        return f"<Task(id={self.task_id}, name='{self.name}')>"


    @classmethod
    async def create_task(
        cls
    ): pass

    async def on_name(
        self
    ): pass

    async def on_description(
        self
    ): pass

    async def on_image_description(
        self
    ): pass

    async def on_image_count(
        self
    ): pass

    async def on_customer(
        self
    ): pass

    async def on_executor(
        self
    ): pass

    async def on_editor(
        self
    ): pass

    async def on_deadline(
        self
    ): pass