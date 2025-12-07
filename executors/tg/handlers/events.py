from aiogram import F, Bot, Dispatcher
from aiogram.types import Message
from modules.logs import executors_logger as logger
from modules.executors_manager import manager

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp

@dp.startup()
async def on_startup():
    logger.info("Telegram bot started.")

@dp.shutdown()
async def on_shutdown():
    logger.info("Telegram bot stopped.")

@dp.callback_query(F.data.startswith("delete_message"))
async def delete_message_callback(callback):
    """Обработчик для удаления сообщения по коллбеку"""
    
    # Проверяем права в группах/супергруппах
    if callback.message.chat.type in ("group", "supergroup"):
        member = await callback.bot.get_chat_member(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id
        )
        # Проверяем, может ли пользователь удалять сообщения
        can_delete = (
            member.status in ("creator", "administrator") and 
            (member.status == "creator" or getattr(member, "can_delete_messages", False))
        )
        if not can_delete:
            await callback.answer("У вас нет прав на удаление сообщений", show_alert=True)
            return
    
    id_list = callback.data.split()[1:]  # Получаем список ID сообщений из callback_data
    
    try:
        await callback.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
    
    for msg_id in id_list:
        try:
            await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=int(msg_id))
        except Exception as e:
            logger.error(f"Error deleting message ID {msg_id}: {e}")