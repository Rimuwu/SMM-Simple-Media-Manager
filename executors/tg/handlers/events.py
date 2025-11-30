

from aiogram import F, Bot, Dispatcher
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

@dp.callback_query(F.data == "delete_message")
async def delete_message_callback(callback):
    """Обработчик для удаления сообщения по коллбеку"""
    try:
        await callback.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")