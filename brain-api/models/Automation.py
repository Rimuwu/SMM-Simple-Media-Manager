from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON, UUID
from enum import Enum
from typing import Optional
from uuid import UUID as _UUID
from database.connection import Base
from database.annotated_types import intAutoPK


class AutomationTypes(str, Enum):
    """Типы автоматизации"""
    auto_story = "auto_story"
    auto_repost = "auto_repost"
    auto_reaction = "auto_reaction"
    auto_pin = "auto_pin"


class Preset(Base):
    __tablename__ = "presets"

    preset_id: Mapped[intAutoPK]
    name: Mapped[str] = mapped_column(String, nullable=False)

    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    automations: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    clients: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    executor_id: Mapped[Optional[_UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)

    # Связи
    automations_rel: Mapped[list["Automation"]] = relationship("Automation", back_populates="preset")


class Automation(Base):
    __tablename__ = "automations"

    auto_id: Mapped[intAutoPK]
    card_id: Mapped[_UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cards.card_id"), nullable=False)
    preset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("presets.preset_id"), nullable=True)
    type: Mapped[AutomationTypes] = mapped_column(nullable=False)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Связи
    card: Mapped["Card"] = relationship("Card")
    preset: Mapped[Optional["Preset"]] = relationship("Preset", back_populates="automations_rel")
