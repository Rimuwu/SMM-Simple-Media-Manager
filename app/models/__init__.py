# Импортируем все модели в правильном порядке для SQLAlchemy
from .User import User
from .task.Task import Task
from .card.Card import Card
from .Scene import Scene
from .card.Tag import Tag
from .ScheduledTask import ScheduledTask
from .card.CardContent import CardContent
from .card.ClientSetting import ClientSetting
from .card.ClientEntity import Entity

# Импортируем энумы из глобального модуля
from modules.enums import UserRole, CardStatus
# from global_modules.classes.enums import MessageType

__all__ = [
    "User", "UserRole",
    "Task",
    "Card", "CardStatus",
    "Tag",
    "ScheduledTask", "TaskStatus",
    "CardContent", "ClientSetting", "Entity",
    "Scene"
]