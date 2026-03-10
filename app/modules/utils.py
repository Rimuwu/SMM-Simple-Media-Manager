from typing import Optional
from aiogram import Bot
import time

max_live = 3600
cache_users = {}

async def get_telegram_user(bot: Bot, telegram_id: int):
    """Получить информацию о пользователе Telegram по его ID"""
    try:
        if telegram_id in cache_users:
            if time.time() - cache_users[telegram_id]['timestamp'] <= max_live:
                return cache_users[telegram_id]['user']

        user = await bot.get_chat(telegram_id)
        cache_users[telegram_id] = {
            'user': user, 'timestamp': time.time()
        }
        return user
    except Exception as e:
        return None

async def get_display_name(
                    telegram_id: int,
                    bot=None,
                    short: bool = False
                ) -> str:
    """
    Получить отображаемое имя пользователя через Telegram API.

    Args:
        telegram_id: ID пользователя в Telegram
        bot: Экземпляр бота для получения имени из Telegram
        short: Если True — только полное имя без username
    """
    if bot and telegram_id:
        chat = await get_telegram_user(bot, telegram_id)
        if chat:
            if short:
                return f"{chat.full_name}"
            return f"{chat.full_name} (@{chat.username})" if chat.username else chat.full_name

    return f"user_{telegram_id}"


def get_user_display_name(user) -> str:
    """Получить отображаемое имя пользователя из модели или словаря данных БД."""
    if not user:
        return "Неизвестный"
    # Поддерживает как модель User (атрибуты), так и dict (get)
    name = user.name if hasattr(user, "name") else user.get("name")
    if name:
        return name
    tid = user.telegram_id if hasattr(user, "telegram_id") else user.get("telegram_id", "?")
    return f"user_{tid}"



# кешированная карта тегов: ключ -> запись из БД
_tags_cache: dict[str, dict] | None = None


async def get_tags_map(refresh: bool = False) -> dict[str, dict]:
    """Возвращает карту тегов ``{key: record}``, загруженную из БД.

    При первом вызове загружает теги через модель ``Tag`` и кэширует результат.
    Если ``refresh=True``, выполняется повторная загрузка.
    """
    global _tags_cache
    if _tags_cache is not None and not refresh:
        return _tags_cache

    from app.models.card.Tag import Tag
    try:
        tags_list = await Tag.all_sorted()
    except Exception:
        tags_list = []

    _tags_cache = {t.key: {"key": t.key, "name": t.name, "tag": t.tag, "order": t.order} for t in tags_list}
    return _tags_cache


async def sort_tags(tags: list[str]) -> list[str]:
    """
    Возвращает список ключей тегов, отсортированных по полю ``order`` из БД.

    Args:
        tags: список ключей тегов

    Возвращает:
        новый список ключей, упорядоченный по ``order``
    """
    if not tags:
        return []

    tag_map = await get_tags_map()
    order_map = {k: tag_map.get(k, {}).get('order', 0) for k in tags}
    return sorted(tags, key=lambda k: order_map.get(k, 0))


async def format_tags(tags: list[str]) -> str:
    """
    Форматирует список ключей тегов в строку через запятую, учитывая порядок.

    Сортировка и получение имён берётся из карты тегов
    (см. :func:`get_tags_map`).

    Args:
        tags: список ключей тегов

    Returns:
        строка с именами тегов, отсортированными по order
    """
    if not tags:
        return 'Не указаны'

    tag_map = await get_tags_map()
    sorted_keys = sorted(tags, key=lambda k: tag_map.get(k, {}).get('order', 0))
    def name_for(k: str) -> str:
        return tag_map.get(k, {}).get('name', k)
    return ', '.join(name_for(k) for k in sorted_keys)

def is_valid_telegram_url(url: str) -> bool:
    """Проверяет, что URL допустим для кнопок Telegram (нет подчёркиваний в домене)."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        hostname = parsed.hostname or ''
        # Telegram не принимает подчёркивания в hostname
        return '_' not in hostname and bool(parsed.scheme) and bool(hostname)
    except Exception:
        return False