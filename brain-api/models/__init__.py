# Импортируем все модели в правильном порядке для SQLAlchemy
from .User import User, UserRole
from .Card import Card, CardStatus  
from .Message import Message, MessageType
from .Automation import Automation, AutomationTypes, Preset

__all__ = [
    "User", "UserRole",
    "Card", "CardStatus", 
    "Message", "MessageType",
    "Automation", "AutomationTypes", "Preset"
]