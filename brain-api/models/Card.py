from sqlalchemy import String, Text, Boolean, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON, UUID
from datetime import datetime
from typing import Optional
from uuid import UUID as _UUID
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK, createAT, updateAT
from global_modules.classes.enums import CardStatus

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from models.User import User
    from models.CardContent import CardContent
    from models.CardEditorNote import CardEditorNote
    from models.ClientSetting import ClientSetting
    from models.Entity import Entity
    from sqlalchemy.ext.asyncio import AsyncSession

class Card(Base, AsyncCRUDMixin):
    __tablename__ = "cards"

    card_id: Mapped[uuidPK]
    status: Mapped[CardStatus] = mapped_column(nullable=False, default=CardStatus.pass_)

    task_id: Mapped[int] = mapped_column(nullable=False)

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Связь с пользователем (заказчиком)
    customer_id: Mapped[Optional[_UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    customer: Mapped[Optional["User"]] = relationship(
        "User", back_populates="cards", foreign_keys=[customer_id])

    # Исполнитель
    executor_id: Mapped[Optional[_UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    executor: Mapped[Optional["User"]] = relationship(
        "User", back_populates="executed_cards", foreign_keys=[executor_id])

    editor_id: Mapped[Optional[_UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    editor: Mapped[Optional["User"]] = relationship(
        "User", back_populates="edited_cards", foreign_keys=[editor_id])

    # Контент и метаданные (перенесены в отдельную таблицу `card_contents`)
    contents: Mapped[list["CardContent"]] = relationship(
        "CardContent", back_populates="card", cascade="all, delete-orphan")
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

    # Замена JSON-поля `editor_notes` отдельной таблицей `card_editor_notes`
    editor_notes_entries: Mapped[list["CardEditorNote"]] = relationship(
        "CardEditorNote", back_populates="card", cascade="all, delete-orphan")

    # Настройки по клиентам. Перенесены в `client_settings`
    clients_settings_entries: Mapped[list["ClientSetting"]] = relationship(
        "ClientSetting", back_populates="card", cascade="all, delete-orphan")

    # Ентити для по клиентам. Перенесены в `entities`
    entities_entries: Mapped[list["Entity"]] = relationship(
        "Entity", back_populates="card", cascade="all, delete-orphan")

    # Временные метки
    created_at: Mapped[createAT]
    updated_at: Mapped[updateAT]


    def __repr__(self) -> str:
        return f"<Card(id={self.card_id}, name='{self.name}', status='{self.status}')>"

    @property
    def content(self) -> dict:
        """Compatibility property: возвращает словарь client_key->text"""
        items = getattr(self, 'contents', []) or []
        latest: dict[str, tuple[str, datetime]] = {}
        for c in items:
            key = c.client_key or 'all'
            created = getattr(c, 'created_at', datetime.min)
            if key not in latest or created > latest[key][1]:
                latest[key] = (c.text, created)
        return {k: v[0] for k, v in latest.items()}

    @property
    def editor_notes(self) -> list:
        items = getattr(self, 'editor_notes_entries', []) or []
        items_sorted = sorted(items, key=lambda n: getattr(n, 'created_at', datetime.min))
        return [n.to_dict() for n in items_sorted]

    @property
    def clients_settings(self) -> dict:
        items = getattr(self, 'clients_settings_entries', []) or []
        res: dict = {}
        for s in items:
            key = s.client_key or 'all'
            res.setdefault(key, {}).update(s.data or {})
        return res

    @property
    def entities(self) -> dict:
        items = getattr(self, 'entities_entries', []) or []
        res: dict = {}
        for e in items:
            key = e.client_key or 'all'
            res.setdefault(key, []).append(e.to_dict())
        return res

    # ---- Backwards compatible accessors (work with new normalized tables) ----
    async def get_content(self, session: Optional["AsyncSession"] = None, client_key: Optional[str] = None) -> List["CardContent"]:
        from models.CardContent import CardContent
        filters: dict[str, object] = {"card_id": self.card_id}
        if client_key is not None:
            filters["client_key"] = client_key
        return await CardContent.filter_by(session=session, **filters)

    async def add_content(self, text: str, client_key: Optional[str] = None, session: Optional["AsyncSession"] = None):
        from models.CardContent import CardContent
        return await CardContent.create(session=session, card_id=self.card_id, text=text, client_key=client_key)

    async def get_editor_notes(self, session: Optional["AsyncSession"] = None):
        from models.CardEditorNote import CardEditorNote
        notes = await CardEditorNote.filter_by(session=session, card_id=self.card_id)
        notes.sort(key=lambda n: getattr(n, 'created_at', datetime.min))
        return notes

    async def add_editor_note(self, author: Optional[str], content: str, session: Optional["AsyncSession"] = None):
        from models.CardEditorNote import CardEditorNote
        return await CardEditorNote.create(session=session, card_id=self.card_id, author=author, content=content)

    async def get_clients_settings(self, session: Optional["AsyncSession"] = None, client_key: Optional[str] = None):
        from models.ClientSetting import ClientSetting
        filters: dict[str, object] = {"card_id": self.card_id}
        if client_key is not None:
            filters["client_key"] = client_key
        return await ClientSetting.filter_by(session=session, **filters)

    async def set_client_setting(self, client_key: str, data: dict, type: Optional[str] = None, session: Optional["AsyncSession"] = None):
        from models.ClientSetting import ClientSetting
        obj, created = await ClientSetting.first_or_create(session=session, card_id=self.card_id, client_key=client_key, defaults={"data": data, "type": type})
        if not created:
            await obj.update(session=session, data=data, type=type)
        return obj

    async def get_entities(self, session: Optional["AsyncSession"] = None, client_key: Optional[str] = None):
        from models.Entity import Entity
        filters: dict[str, object] = {"card_id": self.card_id}
        if client_key is not None:
            filters["client_key"] = client_key
        return await Entity.filter_by(session=session, **filters)

    async def set_entity(self, client_key: str, data: dict, type: Optional[str] = None, session: Optional["AsyncSession"] = None):
        from models.Entity import Entity
        obj, created = await Entity.first_or_create(session=session, card_id=self.card_id, client_key=client_key, defaults={"data": data, "type": type})
        if not created:
            await obj.update(session=session, data=data, type=type)
        return obj