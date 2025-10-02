from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON, UUID
from enum import Enum
from datetime import datetime
from typing import Optional
from uuid import UUID as _UUID
from database.connection import Base
from database.annotated_types import uuidPK, createAT
from global_modules.classes.enums import CardStatus


class Card(Base):
    __tablename__ = "cards"

    card_id: Mapped[uuidPK]
    status: Mapped[CardStatus] = mapped_column(nullable=False, default=CardStatus.pass_)

    task_id: Mapped[int] = mapped_column(nullable=False)

    # name: Mapped[str] = mapped_column(String, nullable=False)
    # description: Mapped[str] = mapped_column(Text, nullable=True)

    # Связь с пользователем (заказчиком)
    customer_id: Mapped[Optional[_UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    customer: Mapped[Optional["User"]] = relationship("User", back_populates="cards", foreign_keys=[customer_id])

    # Исполнитель
    executor_id: Mapped[Optional[_UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    executor: Mapped[Optional["User"]] = relationship("User", back_populates="executed_cards", foreign_keys=[executor_id])

    # JSON поля
    # clients: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # need_check: Mapped[bool] = mapped_column(Boolean, default=True)

    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)