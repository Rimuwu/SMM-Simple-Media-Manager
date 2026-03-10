from sqlalchemy import String, Integer, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK
from modules.enums import UserRole, Department
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from models.Card import Card
    from models.Task import Task

class User(Base, AsyncCRUDMixin):
    __tablename__ = "users"

    user_id: Mapped[uuidPK]
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(nullable=False, default=UserRole.copywriter)

    task_per_year: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    task_per_month: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tasks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    tasks_checked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tasks_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    canceled_tasks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_images: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    fall_tasks: Mapped[int] = mapped_column(Integer, nullable=False, default=0) # Просроченные задачи

    department: Mapped[Department] = mapped_column(nullable=False, default=Department.without_department)
    about: Mapped[str] = mapped_column(String, nullable=True, default=None)

    can_pick: Mapped[bool] = mapped_column(nullable=False, default=False) # Может ли заказчик выдать задание исполнителю как личное задание

    # Связи
    # Задания, созданные пользователем как заказчик
    own_tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="customer", foreign_keys="Task.customer_id")
    # Задания, в которых пользователь является исполнителем
    executed_tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="executor", foreign_keys="Task.executor_id")

    def __repr__(self) -> str:
        return f"<User(id={self.user_id}, telegram_id={self.telegram_id}, role='{self.role}')>"

    # ── Классовые методы-запросы ─────────────────────────────────────────────

    @classmethod
    async def find(
        cls,
        telegram_id=None,
        role=None,
        user_id=None,
        department=None,
    ) -> "list[User]":
        """Найти пользователей по произвольному набору фильтров."""
        from uuid import UUID as _UUID

        filters: dict = {}
        if telegram_id is not None:
            filters["telegram_id"] = telegram_id
        if role is not None:
            filters["role"] = role
        if department is not None:
            filters["department"] = department
        if user_id is not None:
            filters["user_id"] = _UUID(str(user_id))
        return await cls.filter_by(**filters) if filters else await cls.get_all()

    @classmethod
    async def by_telegram(cls, telegram_id: int) -> "Optional[User]":
        """Получить пользователя по Telegram ID."""
        return await cls.get_by_key("telegram_id", telegram_id)

    @classmethod
    async def role_for(cls, telegram_id: int) -> "Optional[str]":
        """Вернуть строковое значение роли для пользователя с данным telegram_id."""
        user = await cls.by_telegram(telegram_id)
        return user.role.value if user else None