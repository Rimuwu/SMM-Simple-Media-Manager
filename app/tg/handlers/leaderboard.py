from typing import Any
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from modules.exec.executors_manager import manager
from models.User import User
from app.modules.components.logs import logger
from tg.filters.authorize import Authorize
from modules.utils import get_user_display_name
from tg.filters.in_dm import InDMorWorkGroup

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp  # type: ignore
bot: Bot = client_executor.bot  # type: ignore

async def get_leaderboard_text(period: str = 'all') -> str:
    """
    Получает текст лидерборда для указанного периода.
    period: 'all', 'year', 'month'
    """
    try:
        # Получаем всех пользователей
        users = [u.to_dict() for u in await User.get_all()]
        
        if not users:
            return "❌ Не удалось загрузить данные лидерборда."
        
        users = [u for u in users if isinstance(u, dict)]
        
        # Выбираем поле в зависимости от периода
        if period == 'month':
            field = 'task_per_month'
            period_name = 'месяц'
            emoji = '📅'
        elif period == 'year':
            field = 'task_per_year'
            period_name = 'год'
            emoji = '📆'
        else:
            field = 'tasks'
            period_name = 'всё время'
            emoji = '🏆'
        
        # Сортируем по количеству задач
        sorted_users = sorted(users, 
                              key=lambda u: u.get(field, 0), 
                              reverse=True
                              )

        # Формируем текст
        text_lines = [f"{emoji} <b>Лидерборд за {period_name}</b>\n"]

        medals = ['🥇', '🥈', '🥉']

        idx = -1
        for user in sorted_users[:10]:  # Топ 10
            tasks_count = user.get(field, 0)

            if tasks_count == 0:
                continue
            else:
                idx += 1

            telegram_id = user.get('telegram_id')
            name = get_user_display_name(user) if telegram_id else "Неизвестный"

            # Определяем эмодзи позиции
            if idx < 3:
                position = medals[idx]
            else:
                position = f" {idx + 1}."

            text_lines.append(
                f"• {position} <b>{name}</b> — {tasks_count} задач")

        if len(text_lines) == 1:
            text_lines.append("\n<i>Пока нет данных для отображения.</i>")
        
        return "\n".join(text_lines)
        
    except Exception as e:
        logger.error(f"Ошибка получения лидерборда: {e}")
        return f"❌ Ошибка: {str(e)[:100]}"


@dp.message(Command("leaderboard"), Authorize(), InDMorWorkGroup())
async def leaderboard_command(message: Message):
    """
    Команда /leaderboard - показывает лидерборд
    Можно указать период: /leaderboard month, /leaderboard year, /leaderboard all
    """
    if not message.text:
        return
        
    args = message.text.split()
    
    period = 'all'
    if len(args) > 1:
        arg = args[1].lower()
        if arg in ['month', 'месяц', 'm']:
            period = 'month'
        elif arg in ['year', 'год', 'y']:
            period = 'year'
        elif arg in ['all', 'всё', 'все', 'a']:
            period = 'all'

    text = await get_leaderboard_text(period)
    
    # Добавляем кнопки для переключения периодов
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Месяц", callback_data="leaderboard_month"),
            InlineKeyboardButton(text="📆 Год", callback_data="leaderboard_year"),
            InlineKeyboardButton(text="🏆 Всё время", callback_data="leaderboard_all"),
        ]
    ])
    
    await message.answer(text, parse_mode="html", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith('leaderboard_'), InDMorWorkGroup())
async def leaderboard_callback(callback):
    """Обработчик кнопок переключения периода лидерборда"""
    period = callback.data.replace('leaderboard_', '')
    
    text = await get_leaderboard_text(period)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Месяц", callback_data="leaderboard_month"),
            InlineKeyboardButton(text="📆 Год", callback_data="leaderboard_year"),
            InlineKeyboardButton(text="🏆 Всё время", callback_data="leaderboard_all"),
        ]
    ])
    
    try:
        await callback.message.edit_text(text, parse_mode="html", reply_markup=keyboard)
    except TelegramBadRequest as e:
        # Игнорируем ошибку если сообщение не изменилось
        if "message is not modified" not in str(e):
            raise
    await callback.answer()
