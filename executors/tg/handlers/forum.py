

from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery
from modules.text_generators import card_executed
from modules.logs import executors_logger as logger
from modules.executors_manager import manager
from aiogram import F
from aiogram.filters import Command

from modules.api_client import brain_api as api
from modules.api_client import get_user_role, get_cards
from modules.api_client import update_card, get_users

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp
bot: Bot = client_executor.bot

@dp.callback_query(F.data == "take_task")
async def create_user(callback: CallbackQuery):

    message_id = callback.message.message_id
    users = await get_users(telegram_id=callback.from_user.id)
    user = users[0] if users else None

    if not user:
        await callback.answer(
            "Вы не зарегистрированы в системе.", show_alert=True)
        return

    cards = await get_cards(
        forum_message_id=message_id
    )

    if not cards:
        await callback.answer(
            "Задание не найдено или уже взято другим исполнителем.", show_alert=True)
        await bot.delete_message(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id
        )
        return

    card = cards[0]
    card_id = card['card_id']

    if not card:
        await callback.answer(
            "Задание не найдено.", show_alert=True)
        return 
    
    if card['executor_id'] is not None:
        await callback.answer(
            "Задание уже взято другим исполнителем.", show_alert=True)
        return

    await card_executed(
        card_id=card_id,
        telegram_id=callback.from_user.id
    )