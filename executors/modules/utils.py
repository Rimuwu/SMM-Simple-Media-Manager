from aiogram import Bot, Dispatcher
from aiogram.types import Message

async def get_telegram_user(bot: Bot, telegram_id: int):
    """Получить информацию о пользователе Telegram по его ID"""
    try:
        user = await bot.get_chat(telegram_id)
        return user
    except Exception as e:
        return None