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

class Department(str, Enum):
    """Отделы"""

    it = "it" # IT отдел
    design = "design" # Дизайн отдел
    cosplay = "cosplay" # Отдел косплея
    craft = "craft" # Ремесленный отдел
    media = "media" # Медиа отдел
    board_games = "board_games" # Отдел настольных игр
    smm = "smm" # SMM отдел
    judging = "judging" # Отдел судейства
    streaming = "streaming" # Отдел стриминга

    without_department = "without_department" # Без отдела

class CardType(str, Enum):
    """Типы карточек"""

    public = "public"
    private = "private"

class ChangeType(str, Enum):
    """Типы изменений в карточке"""
    
    DEADLINE = "deadline"
    COMMENT = "comment"
    NAME = "name"
    DESCRIPTION = "description"