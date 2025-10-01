import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from modules.executor import BaseExecutor
from modules.logs import executors_logger as logger

class TelegramExecutor(BaseExecutor):
    """Исполнитель для Telegram"""

    def __init__(self, config: dict, executor_name: str = "telegram"):
        super().__init__(config, executor_name)
        self.token = config.get("token")
        self.bot = Bot(
            token=self.token) if self.token else None
        self.dp = Dispatcher()

    def setup_handlers(self):
        """Настройка обработчиков"""
        import tg.handlers
        from .oms import register_handlers

        register_handlers(self.dp)

    async def send_message(self, chat_id: str, text: str) -> dict:
        """Отправить сообщение"""
        try:
            result = await self.bot.send_message(chat_id, text)
            return {"success": True, "message_id": result.message_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def edit_message(self, chat_id: str, message_id: str, text: str) -> dict:
        """Изменить сообщение"""
        try:
            await self.bot.edit_message_text(text, chat_id, int(message_id))
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete_message(self, chat_id: str, message_id: str) -> dict:
        """Удалить сообщение"""
        try:
            await self.bot.delete_message(chat_id, int(message_id))
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def start_polling(self):
        """Запустить пуллинг"""
        self.setup_handlers()

        while self.is_running:
            try:
                await self.dp.start_polling(self.bot)
            except Exception as e:
                print(f"TG Polling error: {e}")
                await asyncio.sleep(5)

    def is_available(self) -> bool:
        """Проверить доступность"""
        return self.token is not None and self.bot is not None

    def get_type(self) -> str:
        """Получить тип"""
        return "telegram"

