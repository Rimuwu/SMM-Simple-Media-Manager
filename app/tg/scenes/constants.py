"""
Общие константы для сцен: маппинги отделов, ролей и статусов.
"""
from global_modules.classes.enums import Department, CardStatus

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
