# Импортируем все модели в правильном порядке для SQLAlchemy
from .User import User
from .Task import Task
from .Card import Card
from .Scene import Scene
from .Tag import Tag
from .ScheduledTask import ScheduledTask
from .CardContent import CardContent
from .ClientSetting import ClientSetting
from .Entity import Entity
# from .Message import Message
# from .Automation import Automation, Preset

# Импортируем энумы из глобального модуля
from modules.enums import UserRole, CardStatus, AutomationTypes
# from global_modules.classes.enums import MessageType

__all__ = [
    "User", "UserRole",
    "Task",
    "Card", "CardStatus",
    "Tag",
    "ScheduledTask", "TaskStatus",
    "CardContent", "ClientSetting", "Entity",
    # "Message", "MessageType",
    # "Automation", "AutomationTypes", "Preset"
]