from sqlalchemy import String, Text, DateTime, ForeignKey
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
    from models.Card import Card


class Task(Base, AsyncCRUDMixin):
    __tablename__ = "tasks"

    task_id: Mapped[uuidPK]

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Заказчик задания
    customer_id: Mapped[Optional[_UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )
    customer: Mapped[Optional["User"]] = relationship(
        "User", back_populates="own_tasks", foreign_keys=[customer_id]
    )

    # Исполнитель задания
    executor_id: Mapped[Optional[_UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )
    executor: Mapped[Optional["User"]] = relationship(
        "User", back_populates="executed_tasks", foreign_keys=[executor_id]
    )

    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Посты (карточки), привязанные к этому заданию
    cards: Mapped[List["Card"]] = relationship(
        "Card", back_populates="task", foreign_keys="Card.task_id"
    )

    created_at: Mapped[createAT]
    updated_at: Mapped[updateAT]

    def __repr__(self) -> str:
        return f"<Task(id={self.task_id}, name='{self.name}')>"
