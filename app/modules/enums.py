from enum import Enum


class CardStatus(str, Enum):
    """Статусы карточек"""

    create = "create" # Создана, ждёт одобрения создания

    wait_start = "wait_start" # Одобрена, ждёт начала работы
    working = "working" # В работе
    review = "review" # На проверке
    ready = "ready" # Готово к публикации

    sending = "sending" # Публикуется
    sent = "sent" # Отправлено

class MessageType(str, Enum):
    """Типы сообщений"""

    # Сообщение на форуме задач
    forum_message = "forum_message"

    # Сообщение с итоговым превью
    complete_preview = "complete_preview"
    complete_info = "complete_info"
    complete_entitity = "complete_entity"

    # Сообщение с задачей дизайну
    design_task = "design_task"

    # Итоговый пост
    final_post = "final_post"
    final_entity = "final_entity"

class UserRole(str, Enum):
    """Роли пользователей в системе"""

    # Брать задания, редактировать, отправлять на проверку, создавать для себя
    copywriter = "copywriter"
    # Копирайтер + брать на проверку и одобрять к публикации
    editor = "editor"
    # Создавать и отслеживать прогресс
    customer = "customer"

    # Всё
    admin = "admin"

    # Авто-роль для счёта выполненных задач
    designer = "designer"

class Department(str, Enum):
    """Отделы"""

    it = "it" # IT отдел
    design = "design" # Дизайн отдел
    cosplay = "cosplay" # Отдел косплея
    craft = "craft" # Крфат отдел
    media = "media" # Медиа отдел
    board_games = "board_games" # Отдел настольных игр
    smm = "smm" # SMM отдел
    judging = "judging" # Отдел судейства
    streaming = "streaming" # Отдел трансляций

    without_department = "without_department" # Без отдела