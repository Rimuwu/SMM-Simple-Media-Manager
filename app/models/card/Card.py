from sqlalchemy import String, Text, Boolean, DateTime, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON, UUID
from datetime import datetime
from typing import Optional
from uuid import UUID as _UUID
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK, createAT, updateAT
from modules.enums import CardStatus

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.task.Task import Task
    from app.models.card.CardContent import CardContent
    from app.models.card.ClientSetting import ClientSetting
    from app.models.card.ClientEntity import Entity
    from app.models.Message import CardMessage
    from models.ScheduledTask import ScheduledTask

class Card(Base, AsyncCRUDMixin):
    __tablename__ = "cards"

    card_id: Mapped[uuidPK]
    status: Mapped[CardStatus] = mapped_column(nullable=False, default=CardStatus.pass_)

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True)

    # Контент и метаданные (перенесены в отдельную таблицу `card_contents`)
    contents: Mapped[list["CardContent"]] = relationship(
        "CardContent", back_populates="card", cascade="all, delete-orphan", lazy="selectin")
    clients: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True, default=[])

    # Проверка редактором
    need_check: Mapped[bool] = mapped_column(Boolean, default=True)
    # Завершение без отправки
    need_send: Mapped[bool] = mapped_column(Boolean, default=True)
    # Право отправить работу заказчиком самостоятельно
    need_send_right: Mapped[bool] = mapped_column(Boolean, default=True)

    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True, default=[])

    # Дополнительные поля для управления карточками
    send_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Список имён файлов
    post_images: Mapped[dict[str, str]] = mapped_column(JSON, nullable=True, default={})

    # ID записи в календаре
    calendar_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Задание, к которому привязан этот пост
    task_id: Mapped[Optional[_UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.task_id"), nullable=True)
    task: Mapped[Optional["Task"]] = relationship(
        "Task", back_populates="cards", foreign_keys=[task_id], lazy="selectin")

    # Настройки по клиентам. Перенесены в `client_settings`
    clients_settings_entries: Mapped[list["ClientSetting"]] = relationship(
        "ClientSetting", back_populates="card", cascade="all, delete-orphan",
        lazy="selectin")

    # Ентити для по клиентам. Перенесены в `entities`
    entities_entries: Mapped[list["Entity"]] = relationship(
        "Entity", back_populates="card", cascade="all, delete-orphan",
        lazy="selectin")

    # Сообщения (forum, complete_preview и т.д.)
    messages: Mapped[list["CardMessage"]] = relationship(
        "CardMessage", back_populates="card", cascade="all, delete-orphan", lazy="selectin")

    # Запланированные задачи, связанные с карточкой
    scheduled_tasks: Mapped[list["ScheduledTask"]] = relationship(
        "ScheduledTask", back_populates="card", cascade="all, delete-orphan", lazy="selectin")

    # Временные метки
    created_at: Mapped[createAT]
    updated_at: Mapped[updateAT]


    def __repr__(self) -> str:
        return f"<Card(id={self.card_id}, name='{self.name}', status='{self.status}')>"

    # ── Классовые методы-запросы ─────────────────────────────────────────────

    @classmethod
    async def find(
        cls,
        card_id=None,
        task_id=None,
        status=None,
        need_check=None,
    ) -> "list[Card]":
        """Найти карточки по произвольному набору фильтров.

        Все параметры опциональны; без параметров возвращает все карточки.
        Загружает связанные ``contents`` одним запросом (selectinload).
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from database.connection import session_factory

        async with session_factory() as session:
            query = select(cls).options(selectinload(cls.contents))
            if task_id is not None:
                query = query.where(cls.task_id == _UUID(str(task_id)))
            if card_id is not None:
                try:
                    query = query.where(cls.card_id == _UUID(str(card_id)))
                except Exception:
                    return []
            if status is not None:
                query = query.where(cls.status == status)
            if need_check is not None:
                query = query.where(cls.need_check == need_check)
            result = await session.execute(query)
            return list(result.scalars().all())
