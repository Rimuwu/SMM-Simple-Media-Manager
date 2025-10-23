import asyncio
import random
import vk_api
from modules.executor import BaseExecutor
from typing import Optional, Dict, List, Any
from modules.logs import executors_logger as logger


class VKExecutor(BaseExecutor):
    """Исполнитель для VK через сообщество"""

    def __init__(self, config: dict, executor_name: str = "vk"):
        super().__init__(config, executor_name)
        self.token = config.get("access_token")
        self.group_id = int(config.get("group_id") or 0)

        if self.token:
            self.vk_session = vk_api.VkApi(token=self.token)
            self.vk = self.vk_session.get_api()
        else:
            self.vk_session = None
            self.vk = None

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

    # Методы для работы с постами на стене
    async def create_wall_post(self, text: str, attachments: Optional[List[str]] = None, 
                              from_group: bool = True, signed: bool = False) -> dict:
        """Создать пост на стене сообщества"""
        try:
            params = {
                "owner_id": -abs(self.group_id),  # Отрицательный ID для сообществ
                "message": text,
                "from_group": 1 if from_group else 0,
                "signed": 1 if signed else 0
            }
            
            if attachments:
                params["attachments"] = ",".join(attachments)
            
            result = self.vk.wall.post(**params)
            return {"success": True, "post_id": result["post_id"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def edit_wall_post(self, post_id: str, text: str, 
                            attachments: Optional[List[str]] = None) -> dict:
        """Редактировать пост на стене"""
        try:
            params = {
                "owner_id": -abs(self.group_id),
                "post_id": int(post_id),
                "message": text
            }
            
            if attachments:
                params["attachments"] = ",".join(attachments)
            
            result = self.vk.wall.edit(**params)
            return {"success": True, "post_id": result["post_id"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete_wall_post(self, post_id: str) -> dict:
        """Удалить пост со стены"""
        try:
            self.vk.wall.delete(
                owner_id=-abs(self.group_id),
                post_id=int(post_id)
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_wall_posts(self, count: int = 10, offset: int = 0, 
                            filter_type: str = "owner") -> dict:
        """Получить посты со стены"""
        try:
            result = self.vk.wall.get(
                owner_id=-abs(self.group_id),
                count=count,
                offset=offset,
                filter=filter_type
            )
            return {"success": True, "posts": result["items"], "total_count": result["count"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def pin_wall_post(self, post_id: str) -> dict:
        """Закрепить пост на стене"""
        try:
            self.vk.wall.pin(
                owner_id=-abs(self.group_id),
                post_id=int(post_id)
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def unpin_wall_post(self) -> dict:
        """Открепить пост со стены"""
        try:
            self.vk.wall.unpin(
                owner_id=-abs(self.group_id)
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def create_comment(self, post_id: str, text: str, 
                           attachments: Optional[List[str]] = None) -> dict:
        """Создать комментарий к посту"""
        try:
            params = {
                "owner_id": -abs(self.group_id),
                "post_id": int(post_id),
                "message": text,
                "from_group": 1
            }
            
            if attachments:
                params["attachments"] = ",".join(attachments)
            
            result = self.vk.wall.createComment(**params)
            return {"success": True, "comment_id": result["comment_id"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete_comment(self, comment_id: str) -> dict:
        """Удалить комментарий"""
        try:
            self.vk.wall.deleteComment(
                owner_id=-abs(self.group_id),
                comment_id=int(comment_id)
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def upload_photo_to_wall(self, photo_path: str) -> dict:
        """Загрузить фото для поста на стену"""
        try:
            from vk_api import VkUpload
            upload = VkUpload(self.vk_session)
            
            # Загружаем фото на стену группы
            photo = upload.photo_wall(photo_path, group_id=self.group_id)
            
            # Формируем строку для attachment
            attachment = f"photo{photo[0]['owner_id']}_{photo[0]['id']}"
            
            return {"success": True, "attachment": attachment, "photo_data": photo[0]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def upload_document_to_wall(self, doc_path: str, title: str = None) -> dict:
        """Загрузить документ для поста на стену"""
        try:
            from vk_api import VkUpload
            upload = VkUpload(self.vk_session)
            
            # Загружаем документ
            doc = upload.document_wall(doc_path, group_id=self.group_id, title=title)
            
            # Формируем строку для attachment
            attachment = f"doc{doc['doc']['owner_id']}_{doc['doc']['id']}"
            
            return {"success": True, "attachment": attachment, "document_data": doc['doc']}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_upload_server_wall(self) -> dict:
        """Получить сервер для загрузки фото на стену"""
        try:
            result = self.vk.photos.getWallUploadServer(group_id=self.group_id)
            return {"success": True, "upload_url": result["upload_url"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def schedule_wall_post(self, text: str, publish_date: int, 
                                attachments: Optional[List[str]] = None) -> dict:
        """Запланировать пост на стене"""
        try:
            params = {
                "owner_id": -abs(self.group_id),
                "message": text,
                "publish_date": publish_date,
                "from_group": 1
            }

            if attachments:
                params["attachments"] = ",".join(attachments)

            result = self.vk.wall.post(**params)
            return {"success": True, "post_id": result["post_id"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def start_polling(self):
        logger.info("VK executor started")

        while self.is_running:
            # Просто ждем, пока executor работает
            await asyncio.sleep(1)
        logger.info("VK executor stopped")

    def is_available(self) -> bool:
        """Проверить доступность"""
        return self.token is not None and self.vk is not None

    def get_type(self) -> str:
        """Получить тип"""
        return "vk"