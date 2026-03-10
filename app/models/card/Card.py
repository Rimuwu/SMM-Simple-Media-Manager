from sqlalchemy import String, Text, Boolean, DateTime, BigInteger, ForeignKey, Table, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON, UUID
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID as _UUID
from app.modules.exec import executor
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK, createAT, updateAT
from modules.enums import CardStatus

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.task.Task import Task
    from app.models.card.CardContent import CardContent
    from app.models.card.ClientSetting import ClientSetting
    from app.models.card.ClientEntity import ClientEntity
    from app.models.Message import Message
    from models.ScheduledTask import ScheduledTask
    from app.models.card.Tag import Tag


card_tags = Table(
    "card_tags",
    Base.metadata,
    Column("card_id", UUID(as_uuid=True), ForeignKey("cards.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class Card(Base, AsyncCRUDMixin):
    __tablename__ = "cards"

    id: Mapped[uuidPK]
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

    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary=card_tags, back_populates="cards", lazy="selectin"
    )

    # Дополнительные поля для управления карточками
    send_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Список имён файлов
    post_images: Mapped[dict[str, str]] = mapped_column(JSON, nullable=True, default={})

    # ID записи в календаре
    calendar_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Задание, к которому привязан этот пост
    task_id: Mapped[Optional[_UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    task: Mapped[Optional["Task"]] = relationship(
        "Task", back_populates="cards", foreign_keys=[task_id], lazy="selectin")

    # Настройки по клиентам. Перенесены в `client_settings`
    clients_settings_entries: Mapped[list["ClientSetting"]] = relationship(
        "ClientSetting", back_populates="card", cascade="all, delete-orphan",
        lazy="selectin")

    # Ентити для по клиентам. Перенесены в `entities`
    entities_entries: Mapped[list["ClientEntity"]] = relationship(
        "ClientEntity", back_populates="card", cascade="all, delete-orphan",
        lazy="selectin")

    # Сообщения (forum, complete_preview и т.д.)
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="card", cascade="all, delete-orphan", lazy="selectin")

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


    # Автоматическое создание с привязкой к карточке
    @classmethod
    async def create_card(cls
    ): pass

    # ── Изменение статуса ─────────────────────────────────────────────

    # После создания
    async def to_create(
        self,
        action: str
    ): pass

    # После одобрения
    async def to_wait_start(
        self,
        action: str
    ): pass

    # После начала работы
    async def to_working(
        self,
        action: str
    ): pass

    # После отправки на проверку
    async def to_review(
        self,
        action: str
    ): pass

    # После одобрения к публикации
    async def to_ready(
        self,
        action: str
    ): pass

    # После начала публикации
    async def to_sending(
        self
    ): pass

    # После начала публикации
    async def to_sent(
        self
    ): pass


    # ── Изменение данных (триггеры)─────────────────────────────────────────────

    # Тригер изменения имени
    async def on_name(self): pass

    # Тригер изменения описания
    async def on_description(self): pass

    # Тригер изменения клиентов
    async def on_clients(self): pass

    # Тригер изменения тегов
    async def on_tags(self): pass

    # Тригер изменения времени отправки
    async def on_send_time(self): pass

    # Тригер изменения тз для картинки
    async def on_post_images(self): pass

    # Тригер изменения контента для клиента
    async def on_contents(self): pass

    # Тригер изменения настроект отсылаемых изображений
    async def on_post_images(self): pass

    # Тригер изменения настроек клиента
    async def on_clients_settings(self): pass

    # Тригер изменения ентити клиента
    async def on_entities(self): pass


    async def send_to_tg(self): pass

    async def send_to_vk(self): pass