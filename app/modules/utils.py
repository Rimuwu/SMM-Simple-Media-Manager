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


async def sort_tags(tags: list[str]) -> list[str]:
    """
    Возвращает список ключей тегов, отсортированных по полю ``order`` из БД.

    Если тег отсутствует в базе, он считается имеющим порядок 0 и остаётся в
    текущем положении относительно других отсутствующих. Это удобно, поскольку
    пользователь может передавать произвольный список ключей.

    Args:
        tags: список ключей тегов

    Returns:
        новый список ключей, упорядоченный по ``order``
    """
    if not tags:
        return []
    # импорт внутри функции, чтобы избежать циклических зависимостей
    from modules.exec.brain_client import get_tags

    try:
        db_tags = await get_tags()
    except Exception:
        db_tags = []

    order_map = {t['key']: t.get('order', 0) for t in db_tags}
    return sorted(tags, key=lambda k: order_map.get(k, 0))


async def format_tags(tags: list[str]) -> str:
    """
    Форматирует список ключей тегов в строку через запятую, учитывая порядок.

    Теги сначала сортируются с помощью :func:`sort_tags`, затем каждый
    ключ заменяется на имя из базы. Если имя не найдено, используется сам ключ.
    Для пустого списка возвращается "Не указаны".

    Args:
        tags: список ключей тегов

    Returns:
        строка с именами тегов, отсортированными по order
    """
    if not tags:
        return 'Не указаны'

    # Получаем информацию из базы единожды
    from modules.exec.brain_client import get_tags

    try:
        db_tags = await get_tags()
    except Exception:
        db_tags = []

    order_map = {t['key']: t.get('order', 0) for t in db_tags}
    name_map = {t['key']: t.get('name', t['key']) for t in db_tags}

    sorted_keys = sorted(tags, key=lambda k: order_map.get(k, 0))
    return ', '.join(name_map.get(k, k) for k in sorted_keys)
