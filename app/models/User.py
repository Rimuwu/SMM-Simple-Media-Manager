from sqlalchemy import String, Integer, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK
from modules.enums import UserRole, Department
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models.task.Task import Task

class User(Base, AsyncCRUDMixin):
    __tablename__ = "users"

    id: Mapped[uuidPK]
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
        "Task", back_populates="customer", foreign_keys="Task.customer_id", lazy="selectin")
    # Задания, в которых пользователь является исполнителем
    executed_tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="executor", foreign_keys="Task.executor_id", lazy="selectin")
    # Задания, в которых пользователь является редактором
    edited_tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="editor", foreign_keys="Task.editor_id", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User(id={self.user_id}, telegram_id={self.telegram_id}, role='{self.role}')>"

    # ── Классовые методы-запросы ─────────────────────────────────────────────

    @classmethod
    async def create_user(
        cls
    ): pass

    @classmethod
    async def get_by_telegram_id(
        cls
    ): pass

    @classmethod
    async def get_all_by_role(
        cls
    ): pass

    async def update_role(
        self
    ): pass

    async def update_department(
        self
    ): pass

    async def update_can_pick(
        self
    ): pass

    async def update_about(
        self
    ): pass


    async def notify_user(
        self,
    ): pass
