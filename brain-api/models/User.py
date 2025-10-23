from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK
from global_modules.classes.enums import UserRole


class User(Base, AsyncCRUDMixin):
    __tablename__ = "users"

    user_id: Mapped[uuidPK]
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    tasker_id: Mapped[int] = mapped_column(Integer, nullable=True, default=None)
    role: Mapped[UserRole] = mapped_column(nullable=False, default=UserRole.copywriter)

    # Связи
    cards: Mapped[list["Card"]] = relationship("Card", back_populates="customer", foreign_keys="[Card.customer_id]")
    executed_cards: Mapped[list["Card"]] = relationship("Card", back_populates="executor", foreign_keys="[Card.executor_id]")
