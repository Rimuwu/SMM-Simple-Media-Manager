"""
Общие константы для сцен: маппинги отделов, ролей и статусов.
"""
from modules.enums import Department, CardStatus
from modules.constants import SETTINGS, CLIENTS

# утилита для форматирования тегов с учётом order
from modules.utils import format_tags  # type: ignore

# Маппинг значений отделов на читаемые имена
DEPARTMENT_NAMES: dict[str, str] = {
    Department.it.value: "IT",
    Department.design.value: "Дизайн",
    Department.cosplay.value: "Косплей",
    Department.craft.value: "Крафт",
    Department.media.value: "Медиа",
    Department.board_games.value: "Настольные игры",
    Department.smm.value: "SMM",
    Department.judging.value: "Судейство",
    Department.streaming.value: "Твич",
    Department.without_department.value: "Без отдела",
}

# Читаемые имена ролей
ROLE_NAMES: dict[str, str] = {
    'admin': 'Админ',
    'customer': 'Заказчик',
    'copywriter': 'Копирайтер',
    'editor': 'Редактор',
}

# Иконки ролей
ROLE_ICONS: dict[str, str] = {
    'admin': '👑',
    'customer': '🎩',
    'copywriter': '👤',
    'editor': '🖋️',
}

# Отображаемые имена статусов карточек (ключи — строковые значения enum)
CARD_STATUS_NAMES: dict[str, str] = {
    CardStatus.pass_.value: "⏳ Создано",
    CardStatus.edited.value: "✏️ В работе",
    CardStatus.review.value: "🔍 На проверке",
    CardStatus.ready.value: "✅ Готова",
    CardStatus.sent.value: "🚀 Отправлено",
}


def format_channels(channels: list) -> str:
    """Форматирует список ключей каналов в строку с именами."""
    if not channels:
        return 'Не указаны'

    return ', '.join(CLIENTS.get(ch, {}
           ).get('label', ch) for ch in channels)

