from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from database.connection import Base
from database.annotated_types import uuidPK


class UserRole(str, Enum):
    """Роли пользователей в системе"""
    copywriter = "copywriter"
    editor = "editor"
    customer = "customer"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuidPK]
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    tasker_id: Mapped[str] = mapped_column(String, nullable=True)
    role: Mapped[UserRole] = mapped_column(nullable=False, default=UserRole.customer)

    # Связи
    cards: Mapped[list["Card"]] = relationship("Card", back_populates="customer")
