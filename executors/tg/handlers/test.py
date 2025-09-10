

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from modules.logs import executors_logger as logger
from modules.executors_manager import manager
from aiogram import F
from aiogram.filters import Command

from global_modules.api_client import APIClient

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp

api = APIClient('http://executors:8003')

@dp.message(Command('send_to_me'))
async def send_to_me(message: Message):

    data = {
        'executor_name': 'telegram_executor',
        'chat_id': message.chat.id,
        'text': f'Hello, {message.from_user.full_name}! This is a test message from /send_to_me command.'
    }

    await api.post('/test/send-message', data=data)
