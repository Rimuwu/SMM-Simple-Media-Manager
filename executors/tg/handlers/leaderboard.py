"""
Обработчик команды лидерборда
"""
from typing import Any
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from modules.executors_manager import manager
from modules.api_client import brain_api
from modules.logs import executors_logger as logger
from tg.filters.authorize import Authorize

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp  # type: ignore
bot: Bot = client_executor.bot  # type: ignore


async def get_user_display_name(telegram_id: int) -> str:
    """
    Получает отображаемое имя пользователя по telegram_id.
    Возвращает @username если есть, иначе full_name.
    """
    try:
        chat = await bot.get_chat(telegram_id)
        if chat.username:
            return f"@{chat.username}"
        elif chat.full_name:
            return chat.full_name
        else:
            return f"ID: {telegram_id}"
    except Exception as e:
        logger.warning(f"Не удалось получить данные пользователя {telegram_id}: {e}")
        return f"ID: {telegram_id}"


async def get_leaderboard_text(period: str = 'all') -> str:
    """
    Получает текст лидерборда для указанного периода.
    period: 'all', 'year', 'month'
    """
    try:
        # Получаем всех пользователей
        response, status = await brain_api.get('/user/get', params={})
        
        if status != 200 or not response:
            return "❌ Не удалось загрузить данные лидерборда."
        
        users = [u for u in response if isinstance(u, dict)]
        
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
        sorted_users = sorted(users, key=lambda u: u.get(field, 0), reverse=True)
        
        # Формируем текст
        text_lines = [f"{emoji} **Лидерборд за {period_name}**\n"]
        
        medals = ['🥇', '🥈', '🥉']
        
        for idx, user in enumerate(sorted_users[:10]):  # Топ 10
            tasks_count = user.get(field, 0)
            
            if tasks_count == 0:
                continue
            
            # Получаем имя пользователя через Telegram API
            telegram_id = user.get('telegram_id')
            if telegram_id:
                name = await get_user_display_name(int(telegram_id))
            else:
                name = "Неизвестный"
            
            # Определяем эмодзи позиции
            if idx < 3:
                position = medals[idx]
            else:
                position = f"{idx + 1}."
            
            text_lines.append(f"{position} {name} — *{tasks_count}* задач")
        
        if len(text_lines) == 1:
            text_lines.append("\n_Пока нет данных для отображения._")
        
        return "\n".join(text_lines)
        
    except Exception as e:
        logger.error(f"Ошибка получения лидерборда: {e}")
        return f"❌ Ошибка: {str(e)[:100]}"


@dp.message(Command("leaderboard"), Authorize())
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
    
    await message.answer("⏳ Загрузка лидерборда...")
    
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
    
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith('leaderboard_'))
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
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    except TelegramBadRequest as e:
        # Игнорируем ошибку если сообщение не изменилось
        if "message is not modified" not in str(e):
            raise
    await callback.answer()
