

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from modules.logs import executors_logger as logger
from modules.executors_manager import manager
from aiogram import F
from aiogram.filters import Command

from global_modules.api_client import APIClient

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp

api = APIClient('http://brain:8000')

@dp.message(Command('create_user'))
async def create_user(message: Message):
    """Создать нового пользователя"""
    telegram_id = None
    role = "copywriter"
    tasker_id = None

    args = message.text.split()[1:]
    args_count = len(args)
    if args_count == 0:
        await message.answer("Использование: /create_user <telegram_id> [role] [tasker_id]")
        return

    if args_count >= 1: telegram_id = int(args[0])
    if args_count >= 2: role = args[1]
    if args_count >= 3: tasker_id = args[2]

    existing_user, status_code = await api.get(
        f"/user/telegram/{telegram_id}")

    if status_code == 200:
        await message.answer("Пользователь с таким Telegram ID уже существует.")
        return

    data = {
        "telegram_id": telegram_id,
        "tasker_id": tasker_id,
        "role": role
    }

    user, status_code = await api.post(
        "/user/create", data=data)

    if status_code == 201:
        await message.answer(f"Пользователь создан!\nID: {user.user_id}\nTelegram ID: {user.telegram_id}\nРоль: {user.role}")
    else:
        await message.answer("Ошибка при создании пользователя.")