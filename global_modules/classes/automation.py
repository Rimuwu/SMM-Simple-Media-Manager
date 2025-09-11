from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from global_modules.classes.enums import AutomationTypes


@dataclass
class PresetData:
    preset_id: int
    name: str
    tags: Optional[dict] = None
    automations: Optional[dict] = None
    clients: Optional[dict] = None
    executor_id: Optional[UUID] = None


@dataclass
class AutomationData:
    auto_id: int
    card_id: UUID
    type: AutomationTypes
    preset_id: Optional[int] = None
    settings: Optional[dict] = None
