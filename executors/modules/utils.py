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
                    kaiten_users: dict, 
                    bot=None,
                    tasker_id: Optional[str] = None,
                    short: bool = False
                ) -> str:
    """
    Получить отображаемое имя пользователя.

    Args:
        telegram_id: ID пользователя в Telegram
        tasker_id: ID пользователя в Kaiten
        kaiten_users: Словарь пользователей Kaiten {id: name}
        bot: Экземпляр бота для получения имени из Telegram
    """

    if tasker_id and tasker_id in kaiten_users:
        if bot and telegram_id:
            chat = await get_telegram_user(bot, telegram_id)
            if chat:
                if short:
                    return f"{kaiten_users[tasker_id]}"
                return f"{kaiten_users[tasker_id]} (@{chat.username})" if chat.username else kaiten_users[tasker_id]
        return kaiten_users[tasker_id]

    if bot and telegram_id:

        chat = await get_telegram_user(bot, telegram_id)
        if chat:
            if short:
                return f"{chat.full_name}"
            return f"{chat.full_name} (@{chat.username})" if chat.username else chat.full_name

    return f"user_{telegram_id}"