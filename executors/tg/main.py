import asyncio
from typing import Optional
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from tg.oms.utils import list_to_inline
from tg.oms import scene_manager
from modules.executor import BaseExecutor
from modules.logs import executors_logger as logger
from modules.api_client import get_all_scenes

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
                reply_to_message_id: Optional[int] = None,
                list_markup: Optional[list] = None,
                row_width: int = 3,
                parse_mode: Optional[str] = None
                           ) -> dict:
        """Отправить сообщение"""
        markup = list_to_inline(list_markup or [], row_width=row_width)

        try:
            result = await self.bot.send_message(chat_id, text,
                    reply_to_message_id=reply_to_message_id,
                    reply_markup=markup,
                    parse_mode=parse_mode
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
        markup = list_to_inline(list_markup or [], row_width=row_width)

        try:
            await self.bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=message_id, 
                reply_markup=markup
                )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def edit_message(self, 
                           chat_id: str, 
                           message_id: str, 
                           text: str,
                           parse_mode: Optional[str] = None,
                           list_markup: Optional[list] = None,
                           row_width: int = 3
                           ) -> dict:
        """Изменить сообщение"""
        markup = list_to_inline(list_markup or [], row_width=row_width) if list_markup is not None else None
        
        try:
            await self.bot.edit_message_text(
                text=text, 
                chat_id=chat_id, 
                message_id=int(message_id), 
                parse_mode=parse_mode,
                reply_markup=markup
            )
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
        
        all_scenes = await get_all_scenes()

        for scene_data in all_scenes:

            scene_manager.load_scene_from_db(
                user_id=scene_data['user_id'],
                scene_path=scene_data['scene_path'],
                page=scene_data['page'],
                message_id=scene_data['message_id'],
                data=scene_data['data'],
                bot_instance=self.bot,
                update_message=True
            )

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

