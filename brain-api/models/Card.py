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

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Связь с пользователем (заказчиком)
    customer_id: Mapped[Optional[_UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    customer: Mapped[Optional["User"]] = relationship("User", back_populates="cards", foreign_keys=[customer_id])

    # Исполнитель
    executor_id: Mapped[Optional[_UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    executor: Mapped[Optional["User"]] = relationship("User", back_populates="executed_cards", foreign_keys=[executor_id])

    # JSON поля
    task_id: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    clients: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    need_check: Mapped[bool] = mapped_column(Boolean, default=True)

    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Временные поля
    time_send: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    create_at: Mapped[createAT]

    # Связи
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="card")
    automations: Mapped[list["Automation"]] = relationship("Automation", back_populates="card")
