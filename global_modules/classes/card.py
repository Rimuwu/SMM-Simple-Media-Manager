from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from uuid import UUID
from global_modules.classes.enums import CardStatus


@dataclass
class CardData:
    card_id: UUID
    name: str
    status: CardStatus
    create_at: datetime
    description: Optional[str] = None
    customer_id: Optional[UUID] = None
    executor_id: Optional[UUID] = None
    task_id: Optional[dict] = None
    clients: Optional[dict] = None
    need_check: bool = True
    content: Optional[str] = None
    tags: Optional[dict] = None
    time_send: Optional[datetime] = None
    deadline: Optional[datetime] = None
