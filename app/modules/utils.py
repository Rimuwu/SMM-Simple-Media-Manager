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


def get_user_display_name(user: dict) -> str:
    """Получить отображаемое имя пользователя из словаря данных БД."""
    if not user:
        return "Неизвестный"
    name = user.get('name')
    if name:
        return name
    return f"user_{user.get('telegram_id', '?')}"



# кешированная карта тегов: ключ -> запись из БД
_tags_cache: dict[str, dict] | None = None


async def get_tags_map(refresh: bool = False) -> dict[str, dict]:
    """Возвращает карту тегов, загруженную из БД.

    При первом вызове загружает теги через ``brain_client.get_tags`` и сохраняет
    результат в ``_tags_cache``. Если ``refresh`` установлен, принудительно
    выполняется повторная загрузка.
    """
    global _tags_cache
    if _tags_cache is not None and not refresh:
        return _tags_cache

    from modules.exec.brain_client import get_tags
    try:
        tags_list = await get_tags()
    except Exception:
        tags_list = []

    _tags_cache = {t['key']: t for t in tags_list}
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
