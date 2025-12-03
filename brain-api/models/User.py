from sqlalchemy import String, Integer, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import uuidPK
from global_modules.classes.enums import UserRole, Department


class User(Base, AsyncCRUDMixin):
    __tablename__ = "users"

    user_id: Mapped[uuidPK]
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    tasker_id: Mapped[int] = mapped_column(Integer, nullable=True, default=None)
    role: Mapped[UserRole] = mapped_column(nullable=False, default=UserRole.copywriter)

    task_per_year: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    task_per_month: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tasks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    department: Mapped[Department] = mapped_column(nullable=False, default=Department.without_department)
    about: Mapped[str] = mapped_column(String, nullable=True, default=None)

    # Связи
    cards: Mapped[list["Card"]] = relationship("Card", back_populates="customer", foreign_keys="[Card.customer_id]")
    executed_cards: Mapped[list["Card"]] = relationship("Card", back_populates="executor", foreign_keys="[Card.executor_id]")
