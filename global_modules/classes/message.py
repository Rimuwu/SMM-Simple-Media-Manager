from dataclasses import dataclass
from uuid import UUID
from global_modules.classes.enums import MessageType


@dataclass
class MessageData:
    message_id: int
    card_id: UUID
    type: MessageType
