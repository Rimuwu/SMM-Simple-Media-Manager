from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from global_modules.classes.enums import UserRole


@dataclass
class UserData:
    user_id: UUID
    telegram_id: int
    role: UserRole
    tasker_id: Optional[str] = None
