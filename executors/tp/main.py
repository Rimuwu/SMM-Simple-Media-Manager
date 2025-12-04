import asyncio
import datetime
from pyrogram import Client
from pyrogram.errors import (
    ApiIdInvalid, 
    SessionPasswordNeeded,
    FloodWait,
    UserDeactivated,
    AuthKeyUnregistered
)
from modules.executor import BaseExecutor
from modules.logs import executors_logger as logger
import os

class TelegramPyrogramExecutor(BaseExecutor):
    """Исполнитель для Telegram на основе Pyrogram (User client)"""

    def __init__(self, config: dict, executor_name: str = "telegram_pyrogram"):
        super().__init__(config, executor_name)

        # Получаем конфигурацию
        self.api_id = config.get("api_id")
        self.api_hash = config.get("api_hash")
        self.phone_number = config.get("phone_number")
        self.session_name = config.get("session_name", "tp_session")
        self.workdir = config.get("workdir", "/sessions")
        self.password = config.get("password", None)

        # Инициализируем клиент
        self.client = None
        if self.api_id and self.api_hash:
            self.client = Client(
                name=self.session_name,
                api_id=self.api_id,
                api_hash=self.api_hash,
                phone_number=self.phone_number,
                workdir=self.workdir,
                password=self.password,
                no_updates=True,
                sleep_threshold=33
            )
            # Проверяем наличие сессии при инициализации
            session_file = os.path.join(self.workdir, f"{self.session_name}.session")
            if not os.path.exists(session_file):
                logger.warning(f"Session file not found: {session_file}")
                logger.warning("Telegram Pyrogram executor will be marked as not available")

    async def send_message(self, chat_id: str, text: str, **kwargs) -> dict:
        """Отправить сообщение"""
        try:
            if not self.client or not await self.client.get_me():
                return {"success": False, "error": "Client not initialized or not authorized"}

            # Преобразуем chat_id в int если это возможно
            try:
                chat_id = int(chat_id)
            except ValueError:
                pass  # Оставляем как строку (может быть username)

            message = await self.client.send_message(
                chat_id=chat_id, 
                text=text,
                **kwargs
            )
            
            return {
                "success": True, 
                "message_id": message.id,
                "chat_id": message.chat.id,
                "date": message.date
            }
            
        except FloodWait as e:
            logger.warning(f"FloodWait: waiting {e.value} seconds")
            return {"success": False, "error": f"FloodWait: {e.value} seconds"}
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {"success": False, "error": str(e)}

    async def edit_message(self, chat_id: str, message_id: str, text: str, **kwargs) -> dict:
        """Изменить сообщение"""
        try:
            if not self.client or not await self.client.get_me():
                return {"success": False, "error": "Client not initialized or not authorized"}

            # Преобразуем параметры
            try:
                chat_id = int(chat_id)
                message_id = int(message_id)
            except ValueError:
                return {"success": False, "error": "Invalid chat_id or message_id format"}

            await self.client.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                **kwargs
            )
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            return {"success": False, "error": str(e)}

    async def delete_message(self, chat_id: str, message_id: str) -> dict:
        """Удалить сообщение"""
        try:
            if not self.client or not await self.client.get_me():
                return {"success": False, "error": "Client not initialized or not authorized"}

            # Преобразуем параметры
            try:
                chat_id = int(chat_id)
                message_id = int(message_id)
            except ValueError:
                return {"success": False, "error": "Invalid chat_id or message_id format"}

            await self.client.delete_messages(
                chat_id=chat_id,
                message_ids=message_id
            )
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return {"success": False, "error": str(e)}

    async def forward_message(self, from_chat_id: str, to_chat_id: str, message_id: str) -> dict:
        """Переслать сообщение"""
        try:
            if not self.client or not await self.client.get_me():
                return {"success": False, "error": "Client not initialized or not authorized"}

            # Преобразуем параметры
            try:
                from_chat_id = int(from_chat_id)
                to_chat_id = int(to_chat_id)
                message_id = int(message_id)
            except ValueError:
                return {"success": False, "error": "Invalid chat_id or message_id format"}

            message = await self.client.forward_messages(
                chat_id=to_chat_id,
                from_chat_id=from_chat_id,
                message_ids=message_id
            )
            
            return {
                "success": True,
                "message_id": message.id if hasattr(message, 'id') else None
            }
            
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
            return {"success": False, "error": str(e)}

    async def send_photo(self, chat_id: str, photo: bytes, caption: str = None, **kwargs) -> dict:
        """
        Отправить фото.
        
        Args:
            chat_id: ID чата
            photo: bytes данные фото
            caption: Подпись
        """
        import tempfile
        import os as os_module
        
        try:
            if not self.client or not await self.client.get_me():
                return {"success": False, "error": "Client not initialized or not authorized"}

            try:
                chat_id = int(chat_id)
            except ValueError:
                pass

            # Сохраняем bytes во временный файл
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                tmp_file.write(photo)
                tmp_path = tmp_file.name

            try:
                message = await self.client.send_photo(
                    chat_id=chat_id,
                    photo=tmp_path,
                    caption=caption,
                    **kwargs
                )
                return {"success": True, "message_id": message.id}
            finally:
                # Удаляем временный файл
                os_module.unlink(tmp_path)

        except FloodWait as e:
            logger.warning(f"FloodWait: waiting {e.value} seconds")
            return {"success": False, "error": f"FloodWait: {e.value} seconds"}
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            return {"success": False, "error": str(e)}

    async def send_media_group(self, chat_id: str, media: list, caption: str = None, **kwargs) -> dict:
        """
        Отправить группу медиа.
        
        Args:
            chat_id: ID чата
            media: Список bytes данных фото
            caption: Подпись для первого фото
        """
        import tempfile
        import os as os_module
        from pyrogram.types import InputMediaPhoto
        
        try:
            if not self.client or not await self.client.get_me():
                return {"success": False, "error": "Client not initialized or not authorized"}

            try:
                chat_id = int(chat_id)
            except ValueError:
                pass

            # Сохраняем все фото во временные файлы
            tmp_paths = []
            media_group = []
            
            for idx, photo_data in enumerate(media):
                if isinstance(photo_data, bytes):
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                        tmp_file.write(photo_data)
                        tmp_paths.append(tmp_file.name)
                    
                    # Подпись только для первого
                    photo_caption = caption if idx == 0 else None
                    media_group.append(InputMediaPhoto(tmp_paths[-1], caption=photo_caption))

            if not media_group:
                return {"success": False, "error": "No valid media items"}

            try:
                messages = await self.client.send_media_group(
                    chat_id=chat_id,
                    media=media_group
                )
                first_msg_id = messages[0].id if messages else None
                return {"success": True, "message_id": first_msg_id, "messages_count": len(messages)}
            finally:
                # Удаляем все временные файлы
                for tmp_path in tmp_paths:
                    try:
                        os_module.unlink(tmp_path)
                    except:
                        pass

        except FloodWait as e:
            logger.warning(f"FloodWait: waiting {e.value} seconds")
            return {"success": False, "error": f"FloodWait: {e.value} seconds"}
        except Exception as e:
            logger.error(f"Error sending media group: {e}")
            return {"success": False, "error": str(e)}

    async def schedule_message(self, chat_id: str, text: str, schedule_date: datetime.datetime, **kwargs) -> dict:
        """Запланировать сообщение"""
        try:
            if not self.client or not await self.client.get_me():
                return {"success": False, "error": "Client not initialized or not authorized"}

            # Запланируем сообщение
            await self.client.send_message(
                chat_id=chat_id,
                text=text,
                schedule_date=schedule_date,
                **kwargs
            )

            return {"success": True}

        except Exception as e:
            logger.error(f"Error scheduling message: {e}")
            return {"success": False, "error": str(e)}

    async def schedule_photo(self, chat_id: str, photo: bytes, schedule_date: datetime.datetime, caption: str = None, **kwargs) -> dict:
        """Запланировать фото"""
        import tempfile
        import os as os_module
        
        try:
            if not self.client or not await self.client.get_me():
                return {"success": False, "error": "Client not initialized or not authorized"}

            try:
                chat_id = int(chat_id)
            except ValueError:
                pass

            # Создаём временный файл
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                tmp_file.write(photo)
                tmp_path = tmp_file.name

            try:
                await self.client.send_photo(
                    chat_id=chat_id,
                    photo=tmp_path,
                    caption=caption,
                    schedule_date=schedule_date,
                    **kwargs
                )
                return {"success": True}
            finally:
                try:
                    os_module.unlink(tmp_path)
                except:
                    pass

        except FloodWait as e:
            logger.warning(f"FloodWait: waiting {e.value} seconds")
            return {"success": False, "error": f"FloodWait: {e.value} seconds"}
        except Exception as e:
            logger.error(f"Error scheduling photo: {e}")
            return {"success": False, "error": str(e)}

    async def schedule_media_group(self, chat_id: str, media: list[bytes], schedule_date: datetime.datetime, caption: str = None, **kwargs) -> dict:
        """Запланировать медиа-группу"""
        from pyrogram.types import InputMediaPhoto
        import tempfile
        import os as os_module
        
        try:
            if not self.client or not await self.client.get_me():
                return {"success": False, "error": "Client not initialized or not authorized"}

            try:
                chat_id = int(chat_id)
            except ValueError:
                pass

            # Создаём временные файлы для всех фото
            tmp_paths = []
            media_list = []
            
            for i, photo_bytes in enumerate(media):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                    tmp_file.write(photo_bytes)
                    tmp_paths.append(tmp_file.name)
                    
                    media_list.append(InputMediaPhoto(
                        media=tmp_file.name,
                        caption=caption if i == 0 else None
                    ))

            try:
                await self.client.send_media_group(
                    chat_id=chat_id,
                    media=media_list,
                    schedule_date=schedule_date,
                    **kwargs
                )
                return {"success": True}
            finally:
                # Удаляем все временные файлы
                for tmp_path in tmp_paths:
                    try:
                        os_module.unlink(tmp_path)
                    except:
                        pass

        except FloodWait as e:
            logger.warning(f"FloodWait: waiting {e.value} seconds")
            return {"success": False, "error": f"FloodWait: {e.value} seconds"}
        except Exception as e:
            logger.error(f"Error scheduling media group: {e}")
            return {"success": False, "error": str(e)}

    async def get_chat_info(self, chat_id: str) -> dict:
        """Получить информацию о чате"""
        try:
            if not self.client or not await self.client.get_me():
                return {"success": False, "error": "Client not initialized or not authorized"}

            try:
                chat_id = int(chat_id)
            except ValueError:
                pass  # Оставляем как строку

            chat = await self.client.get_chat(chat_id)
            
            return {
                "success": True,
                "chat": {
                    "id": chat.id,
                    "type": str(chat.type),
                    "title": getattr(chat, 'title', None),
                    "username": getattr(chat, 'username', None),
                    "first_name": getattr(chat, 'first_name', None),
                    "last_name": getattr(chat, 'last_name', None),
                    "members_count": getattr(chat, 'members_count', None)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting chat info: {e}")
            return {"success": False, "error": str(e)}

    async def start_polling(self):
        """Запустить клиент"""
        if not self.client:
            logger.error("Client not initialized")
            return

        # Проверяем доступность перед запуском
        if not self.is_available():
            logger.error("Telegram Pyrogram executor is not available (session not found)")
            return

        while self.is_running:
            try:
                # Проверяем, авторизован ли уже клиент
                if await self.is_authorized():
                    if not self.client.is_connected:
                        await self.client.start()
                else:
                    logger.error("Client not authorized and session not found. Stopping executor.")
                    break

                # Настраиваем хендлеры после запуска клиента
                # self.setup_handlers()

                # Получаем информацию о текущем пользователе
                me = await self.client.get_me()
                logger.info(f"Logged in as: {me.first_name} (@{me.username}) ID: {me.id}")

                # Ожидаем остановки
                while self.is_running:
                    await asyncio.sleep(1)

            except ApiIdInvalid:
                logger.error("Invalid API ID")
                break
            except AuthKeyUnregistered:
                logger.error("Session expired, need to re-authenticate")
                break
            except UserDeactivated:
                logger.error("User account deactivated")
                break
            except SessionPasswordNeeded:
                logger.error("Two-factor authentication enabled, password required")
                break
            except Exception as e:
                logger.error(f"TG Pyrogram error: {e}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Error args: {e.args}")
                logger.exception("Full traceback:")
                await asyncio.sleep(5)
            finally:
                # Не останавливаем клиент здесь, это будет сделано в методе stop()
                pass

    async def stop(self):
        """Остановить клиент"""
        self.is_running = False
        if self.client:
            try:
                if self.client.is_connected:
                    await self.client.stop()
                    logger.info("Telegram Pyrogram client stopped")
            except (ConnectionError, RuntimeError) as e:
                # Клиент уже остановлен или в процессе остановки
                logger.debug(f"Client already stopped or stopping: {e}")
            except Exception as e:
                logger.error(f"Error stopping client: {e}")

    def is_available(self) -> bool:
        """Проверить доступность"""
        # Проверяем базовую конфигурацию
        if not (self.api_id and self.api_hash and self.client):
            return False

        # Проверяем наличие файла сессии
        session_file = os.path.join(self.workdir, f"{self.session_name}.session")
        if not os.path.exists(session_file):
            logger.warning(f"Session file not found: {session_file}. Executor marked as not available.")
            return False
            
        return True

    def get_type(self) -> str:
        """Получить тип исполнителя"""
        return "telegram_pyrogram"

    async def is_authorized(self) -> bool:
        """Проверить авторизацию"""
        try:
            if not self.client:
                return False
                
            # Проверяем наличие файла сессии
            session_file = os.path.join(self.workdir, f"{self.session_name}.session")
            if not os.path.exists(session_file):
                logger.info(f"Session file not found: {session_file}")
                return False
                
            # Пробуем подключиться и получить информацию о пользователе
            if not self.client.is_connected:
                await self.client.connect()
            me = await self.client.get_me()
            return me is not None
        except ConnectionError as e:
            logger.debug(f"Connection error during authorization check: {e}")
            return False
        except Exception as e:
            logger.debug(f"Authorization check failed: {e}")
            return False