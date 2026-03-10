from sqlalchemy import String, Text, Boolean, DateTime, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON, UUID
from datetime import datetime
from typing import Optional
from uuid import UUID as _UUID
from modules.card.card_events import on_send_time
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK, createAT, updateAT
from modules.enums import CardStatus

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from models.User import User
    from models.CardContent import CardContent
    from models.ClientSetting import ClientSetting
    from models.Entity import Entity
    from models.CardMessage import CardMessage
    from models.CardFile import CardFile
    from models.ScheduledTask import ScheduledTask
    from sqlalchemy.ext.asyncio import AsyncSession

class Card(Base, AsyncCRUDMixin):
    __tablename__ = "cards"

    card_id: Mapped[uuidPK]
    status: Mapped[CardStatus] = mapped_column(nullable=False, default=CardStatus.pass_)

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True)

    # Связь с пользователем (заказчиком)
    customer_id: Mapped[Optional[_UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    customer: Mapped[Optional["User"]] = relationship(
        "User", back_populates="cards", foreign_keys=[customer_id])

    # Исполнитель
    executor_id: Mapped[Optional[_UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    executor: Mapped[Optional["User"]] = relationship(
        "User", back_populates="executed_cards", foreign_keys=[executor_id])

    editor_id: Mapped[Optional[_UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
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

    # Список имён файлов
    post_images: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True, default=[])

    calendar_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Настройки по клиентам. Перенесены в `client_settings`
    clients_settings_entries: Mapped[list["ClientSetting"]] = relationship(
        "ClientSetting", back_populates="card", cascade="all, delete-orphan",
        lazy="selectin")

    # Ентити для по клиентам. Перенесены в `entities`
    entities_entries: Mapped[list["Entity"]] = relationship(
        "Entity", back_populates="card", cascade="all, delete-orphan",
        lazy="selectin")

    # Файлы карточки
    files: Mapped[list["CardFile"]] = relationship(
        "CardFile", back_populates="card", cascade="all, delete-orphan")

    # Сообщения (forum, complete_preview и т.д.)
    messages: Mapped[list["CardMessage"]] = relationship(
        "CardMessage", back_populates="card", cascade="all, delete-orphan")

    # Запланированные задачи, связанные с карточкой
    scheduled_tasks: Mapped[list["ScheduledTask"]] = relationship(
        "ScheduledTask", back_populates="card", cascade="all, delete-orphan")

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
        customer_id=None,
        executor_id=None,
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
                query = query.where(cls.task_id == int(task_id))
            if card_id is not None:
                try:
                    query = query.where(cls.card_id == _UUID(str(card_id)))
                except Exception:
                    return []
            if status is not None:
                query = query.where(cls.status == status)
            if customer_id is not None:
                query = query.where(cls.customer_id == _UUID(str(customer_id)))
            if executor_id is not None:
                query = query.where(cls.executor_id == _UUID(str(executor_id)))
            if need_check is not None:
                query = query.where(cls.need_check == need_check)
            result = await session.execute(query)
            return list(result.scalars().all())

    @classmethod
    async def by_message_id(cls, message_id: int) -> "Optional[Card]":
        """Найти карточку по ID сообщения форума или превью."""
        from models.CardMessage import CardMessage

        messages = await CardMessage.filter_by(message_id=message_id)
        if not messages:
            return None
        return await cls.get_by_id(_UUID(str(messages[0].card_id)))

    @classmethod
    async def busy_slots(
        cls, start: Optional[str] = None, end: Optional[str] = None
    ) -> list[dict]:
        """Список занятых временных слотов вида ``{card_id, send_time}``."""
        from sqlalchemy import select
        from database.connection import session_factory

        async with session_factory() as session:
            stmt = select(cls.card_id, cls.send_time).where(cls.send_time.isnot(None))
            if start:
                stmt = stmt.where(cls.send_time >= datetime.fromisoformat(start))
            if end:
                stmt = stmt.where(cls.send_time <= datetime.fromisoformat(end))
            result = await session.execute(stmt)
            return [
                {"card_id": str(cid), "send_time": st.isoformat()}
                for cid, st in result.all()
                if st
            ]

    async def schedule_immediate(self) -> "Card":
        """Запланировать немедленную отправку (now + 5 секунд)."""
        from modules.timezone import now_naive as moscow_now
        from datetime import timedelta

        await on_send_time(
            send_time=moscow_now() + timedelta(seconds=5),
            card = self
        )

        return self

    def to_full_dict(self) -> dict:
        """Расширенный ``to_dict`` — включает виртуальные свойства ``content`` и ``clients_settings``.

        Используйте вместо ``to_dict()`` там, где нужен полный контент карточки.
        """
        result = self.to_dict()
        result["content"] = self.content
        result["clients_settings"] = self.clients_settings
        return result

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

    async def get_content(self, session: Optional["AsyncSession"] = None, client_key: Optional[str] = None) -> List["CardContent"]:
        from models.CardContent import CardContent
        filters: dict[str, object] = {"card_id": self.card_id}
        if client_key is not None:
            filters["client_key"] = client_key
        return await CardContent.filter_by(session=session, **filters)

    async def add_content(self, text: str, client_key: Optional[str] = None, session: Optional["AsyncSession"] = None):
        from models.CardContent import CardContent
        return await CardContent.create(session=session, card_id=self.card_id, text=text, client_key=client_key)

    async def get_clients_settings(self, session: Optional["AsyncSession"] = None, client_key: Optional[str] = None):
        from models.ClientSetting import ClientSetting
        filters: dict[str, object] = {"card_id": self.card_id}
        if client_key is not None:
            filters["client_key"] = client_key
        return await ClientSetting.filter_by(session=session, **filters)

    async def set_client_setting(self, client_key: str, 
                                 data: dict, 
                                 type: Optional[str] = None, 
                                 session: Optional["AsyncSession"] = None):
        from models.ClientSetting import ClientSetting

        result = await ClientSetting.filter_by(
            session=session, card_id=self.card_id, client_key=client_key, type=type, 
        )
        if result:
            obj = result[0]
            await obj.update(session=session, data=data)
            return obj
        else:
            obj = await ClientSetting.create(
                session=session, card_id=self.card_id, client_key=client_key, data=data, type=type
            )
        return obj

    async def set_client_setting_type(self, client_key: str, setting_type: str, data: dict, session: Optional["AsyncSession"] = None):
        """Обновить один ключ setting_type внутри ClientSetting, сохраняя остальные ключи."""
        from models.ClientSetting import ClientSetting
        results = await ClientSetting.filter_by(session=session, card_id=self.card_id, client_key=client_key)
        if results:
            obj = results[0]
            existing = obj.data.copy() if obj.data else {}
            existing[setting_type] = data
            await obj.update(session=session, data=existing)
            return obj
        return await ClientSetting.create(session=session, card_id=self.card_id, client_key=client_key, data={setting_type: data})

    async def get_entities(self, session: Optional["AsyncSession"] = None, client_key: Optional[str] = None):
        from models.Entity import Entity
        filters: dict[str, object] = {"card_id": self.card_id}
        if client_key is not None:
            filters["client_key"] = client_key
        return await Entity.filter_by(session=session, **filters)

    async def get_messages(self, session: Optional["AsyncSession"] = None, message_type: Optional[str] = None):
        """Получить сообщения карточки"""
        from models.CardMessage import CardMessage
        from database.connection import session_factory
        
        # Если сессия не передана, создаём свою
        if session is None:
            async with session_factory() as new_session:
                if message_type:
                    return await CardMessage.filter_by(session=new_session, card_id=self.card_id, message_type=message_type)
                else:
                    return await CardMessage.filter_by(session=new_session, card_id=self.card_id)
        else:
            if message_type:
                return await CardMessage.filter_by(session=session, card_id=self.card_id, message_type=message_type)
            else:
                return await CardMessage.filter_by(session=session, card_id=self.card_id)

    async def get_forum_message(self, session: Optional["AsyncSession"] = None):
        """Получить forum сообщение карточки"""
        messages = await self.get_messages(session=session, message_type='forum')
        return messages[0] if messages else None

    async def add_message(self, message_type: str, message_id: int,
                          data_info: Optional[str] = None, session: Optional["AsyncSession"] = None):
        """Добавить сообщение к карточке"""
        from models.CardMessage import CardMessage
        return await CardMessage.create(session=session, 
                                        card_id=self.card_id, message_type=message_type, message_id=message_id, data_info=data_info)

    async def get_complete_preview_messages(self, session: Optional["AsyncSession"] = None):
        """Получить все сообщения превью карточки (включая посты, инфо и ентити)."""
        # Поддержка старого типа 'complete_preview' и новых типов 'complete_post', 'complete_info', 'complete_entity'
        valid_types = {"complete_preview", "complete_post", "complete_info", "complete_entity"}
        messages = await self.get_messages(session=session)
        return [m for m in messages if m.message_type in valid_types]

    async def get_complete_messages_by_client(self, client_key: Optional[str] = None, session: Optional["AsyncSession"] = None):
        """Вернуть все сообщения превью для конкретного клиента (или все, если client_key=None)."""
        messages = await self.get_complete_preview_messages(session=session)
        if client_key is None:
            return messages
        return [m for m in messages if (m.data_info == client_key)]

    async def delete_complete_messages_by_client(self, client_key: str, session: Optional["AsyncSession"] = None):
        """Удалить все сообщения превью для клиента (DB only)."""
        messages = await self.get_complete_messages_by_client(client_key=client_key, session=session)
        for m in messages:
            await m.delete(session=session)
        return True

    async def add_complete_post_message(self, message_id: int,
                                        data_info: Optional[str] = None, session: Optional["AsyncSession"] = None):
        return await self.add_message(message_type='complete_post', message_id=message_id,
                                      data_info=data_info, session=session)

    async def add_complete_info_message(self, message_id: int,
                                        data_info: Optional[str] = None, session: Optional["AsyncSession"] = None):
        return await self.add_message(message_type='complete_info', message_id=message_id,
                                      data_info=data_info, session=session)

    async def add_complete_entity_message(self, message_id: int,
                                        data_info: Optional[str] = None, session: Optional["AsyncSession"] = None):
        return await self.add_message(message_type='complete_entity', message_id=message_id,
                                      data_info=data_info, session=session)