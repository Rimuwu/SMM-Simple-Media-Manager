import asyncio
import random
import vk_api
from vk_api.vk_api import VkApiMethod
from modules.executor import BaseExecutor
from modules.post_generator import clean_html, convert_hyperlinks_to_vk
from typing import Literal, Optional, Dict, List, Any
from modules.logs import executors_logger as logger


class VKExecutor(BaseExecutor):
    """Исполнитель для VK через сообщество"""

    def __init__(self, config: dict, executor_name: str = "vk"):
        super().__init__(config, executor_name)
        self.token = config.get("access_token")  # Токен группы для постинга
        self.user_token = config.get("user_token")  # Токен пользователя для загрузки фото
        self.group_id = int(config.get("group_id") or 0)

        if self.token:
            self.vk_session = vk_api.VkApi(token=self.token)
            self.vk: VkApiMethod = self.vk_session.get_api()
        else:
            self.vk_session = None
            self.vk = None
        
        # Отдельная сессия для загрузки фото (требует user token)
        if self.user_token:
            self.vk_user_session = vk_api.VkApi(token=self.user_token)
            self.vk_user: VkApiMethod = self.vk_user_session.get_api()
            logger.info("VK: User token загружен для загрузки фото")
        else:
            self.vk_user_session = None
            self.vk_user = None
            logger.warning("VK: User token не указан - загрузка фото на стену будет недоступна")

    def _format_text_for_vk(self, text: str) -> str:
        """Форматирует текст для VK: конвертирует гиперссылки и очищает HTML"""
        text = convert_hyperlinks_to_vk(text)
        return clean_html(text)

    async def send_message(self, chat_id: str, text: str) -> dict:
        """Отправить сообщение"""
        try:
            result = self.vk.messages.send(
                user_id=int(chat_id),
                message=self._format_text_for_vk(text),
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
                message=self._format_text_for_vk(text)
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
                              from_group: bool = True, signed: bool = False,
                              primary_attachments_mode: Literal['grid', None] = 'grid'
                              ) -> dict:
        """Создать пост на стене сообщества"""
        try:
            logger.info(f"VK: Создание поста на стене группы {self.group_id}")
            logger.info(f"VK: Текст: {text[:100]}..." if len(text) > 100 else f"VK: Текст: {text}")
            logger.info(f"VK: Attachments: {attachments}")

            params = {
                "owner_id": -abs(self.group_id),  # Отрицательный ID для сообществ
                "message": self._format_text_for_vk(text),
                "from_group": 1 if from_group else 0,
                "signed": 1 if signed else 0,
            }

            if primary_attachments_mode:
                params["primary_attachments_mode"] = primary_attachments_mode
                logger.info(f"VK: Установлен режим primary_attachments_mode='{primary_attachments_mode}' для поста")

            if attachments:
                params["attachments"] = ",".join(attachments)
                logger.info(f"VK: Добавлены attachments в пост: {params['attachments']}")

            result = self.vk.wall.post(**params)
            logger.info(f"VK: Пост создан успешно, post_id: {result.get('post_id')}")
            return {"success": True, "post_id": result["post_id"]}
        except Exception as e:
            logger.error(f"VK: Ошибка создания поста: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def edit_wall_post(self, post_id: str, text: str, 
                            attachments: Optional[List[str]] = None) -> dict:
        """Редактировать пост на стене"""
        try:
            params = {
                "owner_id": -abs(self.group_id),
                "post_id": int(post_id),
                "message": self._format_text_for_vk(text)
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
        """
        Загрузить фото для поста на стену группы.
        Требует user_token, так как групповой токен не поддерживает photos.getWallUploadServer.
        """
        import requests
        import os
        from modules.file_utils import detect_file_type_by_bytes

        # Проверяем наличие user token
        if not self.vk_user:
            logger.error("VK: User token не настроен - невозможно загрузить фото")
            return {"success": False, "error": "User token not configured. Set VK_USER_TOKEN env variable."}

        max_attempts = 5
        last_error = None

        # Читаем файл для определения типа по magic bytes
        with open(photo_path, 'rb') as f:
            file_content = f.read()
        
        # Определяем тип изображения через общую функцию
        mime_type, extension, file_type = detect_file_type_by_bytes(file_content)
        
        # Формируем имя файла с правильным расширением
        original_filename = os.path.basename(photo_path)
        if '.' in original_filename:
            # Файл уже имеет расширение - используем его
            filename = original_filename
        else:
            # Временный файл без расширения - добавляем определённое расширение
            filename = original_filename + extension
        
        logger.info(f"VK: Загрузка файла {photo_path}, filename={filename}, mime_type={mime_type}, size={len(file_content)} bytes")

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"VK: Попытка {attempt}/{max_attempts} загрузки фото {photo_path} для группы {self.group_id}")

                # Получаем сервер загрузки фото на стену (требует user token)
                upload_server = self.vk_user.photos.getWallUploadServer(group_id=self.group_id)
                upload_url = upload_server['upload_url']
                logger.info(f"VK: Получен сервер загрузки photos: {upload_url[:50]}...")

                # Отправляем с явным указанием имени файла и типа (file_content уже прочитан выше)
                files = {'photo': (filename, file_content, mime_type)}
                response = requests.post(upload_url, files=files)

                # Проверяем ответ сервера
                if response.status_code != 200:
                    logger.warning(f"VK: HTTP {response.status_code}: {response.text[:200]}")
                    last_error = f"HTTP {response.status_code}"
                    if attempt < max_attempts:
                        await asyncio.sleep(2 * attempt)
                        continue
                    else:
                        return {"success": False, "error": last_error}

                try:
                    upload_result = response.json()
                except Exception as json_err:
                    logger.warning(f"VK: Ошибка парсинга JSON: {json_err}, response: {response.text[:200]}")
                    last_error = f"JSON parse error: {response.text[:100]}"
                    if attempt < max_attempts:
                        await asyncio.sleep(2 * attempt)
                        continue
                    else:
                        return {"success": False, "error": last_error}

                logger.info(f"VK: Ответ сервера загрузки: {upload_result}")

                # Проверяем, что фото загружено (photo не пустой и не '[]')
                photo_data_str = upload_result.get('photo', '')
                if not photo_data_str or photo_data_str == '[]':
                    logger.warning(f"VK: Попытка {attempt}/{max_attempts} - фото не загружено на сервер: {upload_result}")
                    last_error = f"Upload failed - empty photo response: {upload_result}"
                    if attempt < max_attempts:
                        await asyncio.sleep(2 * attempt)
                        continue
                    else:
                        logger.error(f"VK: Все {max_attempts} попыток загрузки фото исчерпаны")
                        return {"success": False, "error": last_error}

                # Сохраняем фото (тоже через user token)
                saved_photo = self.vk_user.photos.saveWallPhoto(
                    group_id=self.group_id,
                    photo=upload_result['photo'],
                    server=upload_result['server'],
                    hash=upload_result['hash']
                )
                logger.info(f"VK: Фото сохранено: {saved_photo}")

                if not saved_photo or len(saved_photo) == 0:
                    logger.warning(f"VK: Попытка {attempt}/{max_attempts} - ошибка сохранения фото: {saved_photo}")

                    last_error = "Photo save failed"
                    if attempt < max_attempts:
                        await asyncio.sleep(2 * attempt)
                        continue
                    else:
                        logger.error(f"VK: Все {max_attempts} попыток загрузки фото исчерпаны")
                        return {"success": False, "error": last_error}

                # Формируем attachment
                photo_data = saved_photo[0]
                attachment = f"photo{photo_data['owner_id']}_{photo_data['id']}"
                logger.info(f"VK: Attachment создан успешно с попытки {attempt}: {attachment}")

                return {"success": True, "attachment": attachment, "photo_data": photo_data}

            except Exception as e:
                logger.warning(f"VK: Попытка {attempt}/{max_attempts} - ошибка загрузки фото: {e}")
                last_error = str(e)
                if attempt < max_attempts:
                    await asyncio.sleep(2 * attempt)
                    continue
                else:
                    logger.error(f"VK: Все {max_attempts} попыток загрузки фото исчерпаны", exc_info=True)
                    return {"success": False, "error": last_error}

    async def upload_document_to_wall(self, doc_path: str, 
                                      title: Optional[str] = None) -> dict:
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