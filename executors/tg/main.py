import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from tg.oms.utils import list_to_inline
from modules.executor import BaseExecutor
from modules.logs import executors_logger as logger

class TelegramExecutor(BaseExecutor):
    """Исполнитель для Telegram"""

    def __init__(self, config: dict, executor_name: str = "telegram"):
        super().__init__(config, executor_name)
        self.token = config.get("token")
        self.bot: Bot = Bot(
            token=self.token) if self.token else None # type: ignore
        self.dp: Dispatcher = Dispatcher()

    def setup_handlers(self):
        """Настройка обработчиков"""
        import tg.handlers
        from .oms import register_handlers

        register_handlers(self.dp)

    async def send_message(self, 
                chat_id: str, 
                text: str, 
                reply_to_message_id: int = None,
                list_markup: list = None,
                row_width: int = 3
                           ) -> dict:
        """Отправить сообщение"""
        markup = list_to_inline(list_markup, row_width=row_width)

        try:
            result = await self.bot.send_message(chat_id, text,
                    reply_to_message_id=reply_to_message_id,
                    reply_markup=markup
                                                 )
            return {"success": True, "message_id": result.message_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_markup(self, 
                            chat_id: str, 
                            message_id: int, 
                            list_markup: list, 
                            row_width: int = 3
                            ) -> dict:
        markup = list_to_inline(list_markup, row_width=row_width)
        
        try:
            await self.bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=message_id, 
                reply_markup=markup
                )
            return {"success": True}
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

