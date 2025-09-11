

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from modules.logs import executors_logger as logger
from modules.executors_manager import manager

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp

# @dp.message()
# async def handle_message(message: Message):
#     logger.info(f"TG Message: {message.text}")

@dp.startup()
async def on_startup():
    logger.info("Telegram bot started.")

@dp.shutdown()
async def on_shutdown():
    logger.info("Telegram bot stopped.")