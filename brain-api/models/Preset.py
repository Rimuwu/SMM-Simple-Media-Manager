from sqlalchemy import String, DateTime, ForeignKey, Text, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON, UUID
from datetime import datetime
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK, strPK, createAT, updateAT
from typing import Optional, TYPE_CHECKING, List
from uuid import UUID as PyUUID
from global_modules.classes.enums import CardStatus
from uuid import UUID as _UUID

class Preset(Base, AsyncCRUDMixin):
    """
       Модель шаблонов
    """
    __tablename__ = "presets"

    preset_id: Mapped[uuidPK]
    status: Mapped[CardStatus] = mapped_column(nullable=False, default=CardStatus.pass_)

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    clients: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True, default=[])
    need_check: Mapped[bool] = mapped_column(Boolean, default=True)
    need_send: Mapped[bool] = mapped_column(Boolean, default=True)

    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True, default=[])

    customer_id: Mapped[Optional[_UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.user_id"), nullable=True)
    # Исполнитель
    executor_id: Mapped[Optional[_UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.user_id"), nullable=True)

    # Дополнительные поля
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 
    repeat_interval: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True) 

    # Временные метки
    created_at: Mapped[createAT]
    updated_at: Mapped[updateAT]