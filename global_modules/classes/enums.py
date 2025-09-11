from enum import Enum


class AutomationTypes(str, Enum):
    """Типы автоматизации"""

    auto_story = "auto_story"
    auto_repost = "auto_repost"
    auto_reaction = "auto_reaction"
    auto_pin = "auto_pin"


class CardStatus(str, Enum):
    """Статусы карточек"""

    pass_ = "pass"
    edited = "edited"
    review = "review"
    ready = "ready"

class MessageType(str, Enum):
    """Типы сообщений"""

    can_take = "can_take"
    ready_review = "ready_review"
    ready_post = "ready_post"

class UserRole(str, Enum):
    """Роли пользователей в системе"""

    copywriter = "copywriter"
    editor = "editor"
    customer = "customer"
    admin = "admin"
