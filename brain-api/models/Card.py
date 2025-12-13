from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON, UUID
from datetime import datetime
from typing import Optional
from uuid import UUID as _UUID
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK, createAT, updateAT
from global_modules.classes.enums import CardStatus

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.User import User

class Card(Base, AsyncCRUDMixin):
    __tablename__ = "cards"

    card_id: Mapped[uuidPK]
    status: Mapped[CardStatus] = mapped_column(nullable=False, default=CardStatus.pass_)

    task_id: Mapped[int] = mapped_column(nullable=False)

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Связь с пользователем (заказчиком)
    customer_id: Mapped[Optional[_UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    customer: Mapped[Optional["User"]] = relationship(
        "User", back_populates="cards", foreign_keys=[customer_id])

    # Исполнитель
    executor_id: Mapped[Optional[_UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    executor: Mapped[Optional["User"]] = relationship(
        "User", back_populates="executed_cards", foreign_keys=[executor_id])

    editor_id: Mapped[Optional[_UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    editor: Mapped[Optional["User"]] = relationship(
        "User", back_populates="edited_cards", foreign_keys=[editor_id])

    # Контент и метаданные
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    clients: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True, default=[])
    need_check: Mapped[bool] = mapped_column(Boolean, default=True)
    need_send: Mapped[bool] = mapped_column(Boolean, default=True)

    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True, default=[])

    # Дополнительные поля для управления карточками
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    send_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    image_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_message: Mapped[int] = mapped_column(BigInteger, nullable=True, default=None)

    # Список имён файлов из Kaiten для публикации
    post_images: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True, default=[])

    forum_message_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    # Формат: {"client_key": {"post_id": int, "info_id": int}, ...}
    complete_message_id: Mapped[dict[str, dict]] = mapped_column(JSON, nullable=False, default={})

    calendar_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    editor_notes: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=[])

    # Настройки по клиентам. Например, шаблоны подписей или установка сетки для вк
    clients_settings: Mapped[dict] = mapped_column(JSON, nullable=False, default={})

    # Ентити для по клиентам. Например опрос в телеграме или авто-репост
    entities: Mapped[dict] = mapped_column(JSON, nullable=False, default={})

    # ALTER TABLE cards
    # ADD COLUMN clients_settings JSONB DEFAULT '{}'::jsonb,
    # ADD COLUMN entities JSONB DEFAULT '{}'::jsonb;

    # Временные метки
    created_at: Mapped[createAT]
    updated_at: Mapped[updateAT]


    def __repr__(self) -> str:
        return f"<Card(id={self.card_id}, name='{self.name}', status='{self.status}')>"