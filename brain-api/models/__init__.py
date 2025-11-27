# Импортируем все модели в правильном порядке для SQLAlchemy
from .User import User
from .Card import Card
# from .Message import Message
# from .Automation import Automation, Preset

# Импортируем энумы из глобального модуля
from global_modules.classes.enums import UserRole, CardStatus, AutomationTypes
# from global_modules.classes.enums import MessageType

__all__ = [
    "User", "UserRole",
    "Card", "CardStatus", 
    "ScheduledTask", "TaskStatus",
    # "Message", "MessageType",
    # "Automation", "AutomationTypes", "Preset"
]