import asyncio
import random
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from executor import BaseExecutor


class VKExecutor(BaseExecutor):
    """Исполнитель для VK через сообщество"""

    def __init__(self, config: dict, executor_name: str = "vk"):
        super().__init__(config, executor_name)
        self.token = config.get("token")
        self.group_id = config.get("group_id")
        
        if self.token:
            self.vk_session = vk_api.VkApi(token=self.token)
            self.vk = self.vk_session.get_api()
            self.longpoll = VkLongPoll(self.vk_session, group_id=self.group_id)
        else:
            self.vk_session = None
            self.vk = None
            self.longpoll = None
    
    async def send_message(self, chat_id: str, text: str) -> dict:
        """Отправить сообщение"""
        try:
            result = self.vk.messages.send(
                user_id=int(chat_id),
                message=text,
                random_id=random.getrandbits(64)
            )
            return {"success": True, "message_id": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def edit_message(self, chat_id: str, message_id: str, text: str) -> dict:
        """Изменить сообщение"""
        try:
            self.vk.messages.edit(
                peer_id=int(chat_id),
                message_id=int(message_id),
                message=text
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def delete_message(self, chat_id: str, message_id: str) -> dict:
        """Удалить сообщение"""
        try:
            self.vk.messages.delete(
                message_ids=int(message_id),
                delete_for_all=1
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def start_polling(self):
        """Запустить пуллинг"""
        while self.is_running:
            try:
                for event in self.longpoll.listen():
                    if event.type == VkEventType.MESSAGE_NEW:
                        print(f"VK Message: {event.text}")

                    if not self.is_running:
                        break
            except Exception as e:
                print(f"VK Polling error: {e}")
                await asyncio.sleep(5)

    def is_available(self) -> bool:
        """Проверить доступность"""
        return self.token is not None and self.vk is not None

    def get_type(self) -> str:
        """Получить тип"""
        return "vk"