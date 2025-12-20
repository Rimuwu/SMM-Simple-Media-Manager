"""
Клиент для работы с brain-api.
Предоставляет типизированные wrapper-функции для API запросов.

Используется в executors и других сервисах для взаимодействия с brain-api.
"""
import enum
from typing import Literal, Optional
from global_modules.api_client import APIClient
from global_modules.classes.enums import CardStatus, Department


class BrainAPIClient:
    """
    Клиент для работы с brain-api.
    Предоставляет методы для работы с карточками, пользователями и сценами.
    """
    
    def __init__(self, base_url: str = 'http://brain:8000'):
        self.api = APIClient(base_url)
    
    # ==================== Карточки ====================
    
    async def get_cards(
        self,
        task_id: Optional[str] = None, 
        card_id: Optional[str] = None, 
        status: Optional[CardStatus] = None,
        customer_id: Optional[str] = None,
        executor_id: Optional[str] = None,
        need_check: Optional[bool] = None
    ) -> list[dict]:
        """Получить карточки по различным параметрам"""
        params = {
            "task_id": task_id,
            "card_id": card_id,
            "status": status.value if status else None,
            "customer_id": customer_id,
            "executor_id": executor_id,
            "need_check": need_check
        }
        cards, res_status = await self.api.get("/card/get", params=params)

        if res_status != 200:
            return []

        return cards

    Nothing = Literal['__nothing__']

    async def update_card(
        self,
        card_id: str,
        executor_id: Optional[str | Nothing] = '__nothing__',
        customer_id: Optional[str | Nothing] = '__nothing__',
        need_check: Optional[bool | Nothing] = '__nothing__',
        need_send: Optional[bool | Nothing] = '__nothing__',
        clients: Optional[list[str] | Nothing] = '__nothing__',
        tags: Optional[list[str] | Nothing] = '__nothing__',
        deadline: Optional[str | Nothing] = '__nothing__',
        image_prompt: Optional[str | Nothing] = '__nothing__',
        prompt_sended: Optional[bool | Nothing] = '__nothing__',
        prompt_message: Optional[int | Nothing] = '__nothing__',
        calendar_id: Optional[str | Nothing] = '__nothing__',
        send_time: Optional[str | Nothing] = '__nothing__',
        post_images: Optional[list[str] | Nothing] = '__nothing__',
        description: Optional[str | Nothing] = '__nothing__',
        name: Optional[str | Nothing] = '__nothing__',
        author_id: Optional[str | Nothing] = '__nothing__',
        editor_id: Optional[str | Nothing] = '__nothing__'
    ) -> dict | None:
        """Обновить карточку"""

        data = {
            "card_id": card_id,
            "executor_id": executor_id,
            "customer_id": customer_id,
            "need_check": need_check,
            "need_send": need_send,
            "clients": clients,
            "tags": tags,
            "deadline": deadline,
            "send_time": send_time,
            "image_prompt": image_prompt,
            "prompt_sended": prompt_sended,
            "prompt_message": prompt_message,
            "calendar_id": calendar_id,
            "post_images": post_images,
            "author_id": author_id,
            "description": description,
            "name": name,
            "editor_id": editor_id
        }

        data = {k: v for k, v in data.items() if v != '__nothing__'}
        print(f"Updating card {card_id} with data: {data}")
        card, res_status = await self.api.post("/card/update", data=data,
                                               no_filter_none=True
                                               )

        if res_status != 200:
            return None

        return card

    async def add_editor_note(
        self, 
        card_id: str, 
        content: str, 
        author_user_id: str,
        is_editor_note: bool = True
    ) -> dict | None:
        """Добавить комментарий редактора к карточке"""
        data = {
            "card_id": card_id,
            "content": content,
            "author": author_user_id,
            "is_editor_note": is_editor_note
        }
        
        result, status = await self.api.post(
            "/card/add-comment", data=data)
        
        if status == 200:
            return result
        
        return None

    async def change_card_status(
        self,
        card_id: str,
        status: CardStatus,
        who_changed: str = 'admin',
        comment: Optional[str] = None
    ) -> dict | None:
        """
        Изменить статус карточки через эндпоинт /change-status
        
        Args:
            card_id: UUID карточки
            new_status: Новый статус (CardStatus enum)
            who_changed: Кто изменил статус ('executor' или 'admin')
            comment: Опциональный комментарий при смене статуса
            
        Returns:
            Словарь с результатом или None при ошибке
        """
        data = {
            "card_id": card_id,
            "new_status": status.value,
            "who_changed": who_changed,
            "comment": comment
        }
        
        result, r_status = await self.api.post("/card/change-status", data=data)
        
        if r_status == 200:
            return result

        return None

    # ==================== Пользователи ====================
    
    async def get_user(
        self,
        telegram_id: Optional[int] = None,
        tasker_id: Optional[int] = None,
        role: Optional[str] = None,
        user_id: Optional[str] = None,
        department: Optional[str] = None
                       ):

        users = await self.get_users(telegram_id, tasker_id, role, user_id, department)
        if users:
            return users[0]
        return None

    async def get_users(
        self,
        telegram_id: Optional[int] = None,
        tasker_id: Optional[int] = None,
        role: Optional[str] = None,
        user_id: Optional[str] = None,
        department: Optional[str] = None
    ) -> list[dict]:
        """Получить пользователей по различным параметрам"""
        params = {
            "telegram_id": telegram_id,
            "tasker_id": tasker_id,
            "role": role,
            "user_id": user_id,
            "department": department
        }
        users, res_status = await self.api.get("/user/get", params=params)

        if res_status != 200:
            return []

        return users

    async def get_user_role(self, telegram_id: int) -> str | None:
        """Получить роль пользователя по telegram_id"""
        users = await self.get_users(telegram_id=telegram_id)
        if users:
            return users[0].get('role')
        return None

    async def create_user(
        self,
        telegram_id: int, 
        role: str, 
        tasker_id: Optional[int] = None,
        department: Optional[str] = None,
        about: Optional[str] = None
    ) -> dict | None:
        """Создать нового пользователя"""
        data = {
            "telegram_id": telegram_id,
            "role": role,
            "tasker_id": tasker_id,
            "department": department,
            "about": about
        }
        user, res_status = await self.api.post("/user/create", data=data)
        if res_status in (200, 201):
            return user
        return None

    async def update_user(
        self,
        telegram_id: int,
        role: Optional[str] = None,
        tasker_id: Optional[int] = None,
        department: Optional[Department] = None,
        about: Optional[str] = None
    ) -> dict | None:
        """Обновить пользователя"""
        data = {
            "telegram_id": telegram_id,
            "role": role,
            "tasker_id": tasker_id,
            "department": department.value if department else None,
            "about": about
        }
        user, res_status = await self.api.post("/user/update", data=data)

        if res_status != 200:
            return None

        return user

    async def delete_user(self, telegram_id: int):
        """Удалить пользователя"""
        return await self.api.delete(f"/user/delete?telegram_id={telegram_id}")

    # ==================== Сцены ====================
    
    async def insert_scene(self, user_id: int, data: dict) -> bool:
        """Создание новой сцены в БД"""
        scene_data = {
            "user_id": user_id,
            "scene": data.get("scene"),
            "scene_path": data.get("scene_path"),
            "page": data.get("page"),
            "message_id": data.get("message_id"),
            "data": data.get("data")
        }
        
        scene, res_status = await self.api.post("/scene/create", data=scene_data)
        
        return res_status == 200 and scene is not None

    async def load_scene(self, user_id: int) -> dict | None:
        """Загрузка сцены пользователя из БД"""
        scene, res_status = await self.api.get(f"/scene/get/{user_id}")
        
        if res_status == 200 and scene:
            return scene
        
        return None

    async def update_scene(self, user_id: int, data: dict) -> bool:
        """Обновление сцены в БД"""
        scene_data = {
            "user_id": user_id,
            "scene": data.get("scene"),
            "scene_path": data.get("scene_path"),
            "page": data.get("page"),
            "message_id": data.get("message_id"),
            "data": data.get("data")
        }
        
        scene, res_status = await self.api.post("/scene/update", data=scene_data)
        
        return res_status == 200 and scene is not None

    async def delete_scene(self, user_id: int) -> bool:
        """Удаление сцены пользователя из БД"""
        result, res_status = await self.api.delete(f"/scene/delete/{user_id}")
        
        return res_status == 200

    async def get_all_scenes(self) -> list[dict]:
        """Получить все сцены из БД"""
        scenes, res_status = await self.api.get("/scene/get-all")
        
        if res_status == 200 and scenes:
            return scenes

        return []

    # ==================== Kaiten ====================
    
    async def get_kaiten_users(self, only_virtual: bool = True) -> list[dict]:
        """Получить пользователей из Kaiten с кешированием"""
        params = {'only_virtual': 1 if only_virtual else 0}
        kaiten_users_list, status = await self.api.get(
            '/kaiten/get-users',
            params=params,
            use_cache=True
        )
        
        if status == 200 and kaiten_users_list:
            return kaiten_users_list
        
        return []

    async def get_kaiten_users_dict(self, only_virtual: bool = True) -> dict[int, str]:
        """Получить словарь пользователей из Kaiten {id: full_name} с кешированием"""
        kaiten_users_list = await self.get_kaiten_users(only_virtual)
        return {user['id']: user['full_name'] for user in kaiten_users_list}

    async def get_kaiten_files(self, task_id: str) -> dict | None:
        """Получить файлы задачи из Kaiten"""
        response, status = await self.api.get(
            f"/kaiten/get-files/{task_id}",
            use_cache=False
        )
        
        if status == 200 and response:
            return response
        
        return None

    async def notify_executor(self, card_id: str, message: str) -> bool:
        """
        Отправить уведомление исполнителю карточки.
        
        Args:
            card_id: UUID карточки
            message: Текст уведомления
            
        Returns:
            True если уведомление отправлено успешно
        """
        data = {
            "card_id": str(card_id),
            "message": message
        }
        
        result, status = await self.api.post("/card/notify-executor", data=data)
        
        return status == 200

    async def upload_files_to_card(
        self,
        card_id: str,
        files: list[dict],
        bot = None
    ) -> int:
        """
        Загрузка списка файлов в карточку Kaiten.
        
        Args:
            card_id: UUID карточки
            files: Список файлов в формате:
                [{'file_id': str, 'name': str, 'type': str, 'mime_type': str}, ...]
                или
                [{'data': bytes, 'name': str, 'mime_type': str}, ...]
            bot: Telegram Bot instance для скачивания файлов (если передан file_id)
            
        Returns:
            Количество успешно загруженных файлов
        """
        uploaded_count = 0
        
        for file_info in files:
            try:
                file_name = file_info.get('name', 'file')
                file_type = file_info.get('type', 'document')
                mime_type = file_info.get('mime_type')
                
                # Получаем данные файла
                if 'data' in file_info:
                    # Данные переданы напрямую
                    file_content = file_info['data']
                elif 'file_id' in file_info and bot:
                    # Нужно скачать из Telegram
                    from modules.file_utils import download_telegram_file
                    file_content = await download_telegram_file(bot, file_info['file_id'])

                    if not file_content:
                        print(f"Не удалось скачать файл {file_name}")
                        continue
                else:
                    print(f"Нет данных для файла {file_name}")
                    continue

                success = await self.upload_file(
                    card_id=card_id,
                    file_data=file_content,
                    filename=file_name,
                    content_type=mime_type
                )

                if success:
                    uploaded_count += 1
                    print(f"Файл {file_name} успешно загружен")
                else:
                    print(f"Ошибка загрузки файла {file_name}")

            except Exception as e:
                print(f"Ошибка загрузки файла {file_info.get('name')}: {e}")

        return uploaded_count

    async def upload_file_to_kaiten(
        self, 
        card_id: str, 
        file_data: bytes, 
        file_name: str,
        content_type: Optional[str] = None,
        convert_to_png: bool = True
    ) -> bool:
        """
        Загружает файл в карточку Kaiten.
        
        Args:
            card_id: UUID карточки из базы данных
            file_data: Бинарные данные файла
            file_name: Имя файла
            content_type: MIME тип (определяется автоматически если не указан)
            convert_to_png: Конвертировать изображения в PNG
            
        Returns:
            True если загрузка успешна
        """
        import aiohttp

        try:
            # Определяем тип файла
            is_image = self._is_image_file(file_data, file_name)
            
            # Конвертируем изображения в PNG если нужно
            if is_image and convert_to_png:
                file_data = self._convert_to_png(file_data)
                # Меняем расширение на .png
                if '.' in file_name:
                    file_name = file_name.rsplit('.', 1)[0] + '.png'
                else:
                    file_name = file_name + '.png'
                content_type = 'image/png'
            
            # Нормализуем имя файла (убираем проблемные символы)
            file_name = self._sanitize_filename(file_name, content_type=content_type)
            
            # Определяем content_type если не указан
            if not content_type:
                content_type = self._detect_content_type(file_data, file_name)
            
            # Формируем multipart/form-data
            form_data = aiohttp.FormData()
            form_data.add_field('card_id', str(card_id))
            form_data.add_field(
                'file',
                file_data,
                filename=file_name,
                content_type=content_type
            )
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{self.api.base_url}/kaiten/upload-file',
                    data=form_data
                ) as resp:
                    if resp.status == 200:
                        return True
                    else:
                        error_text = await resp.text()
                        print(f"Ошибка загрузки файла в Kaiten: {error_text}")
                        return False
                        
        except Exception as e:
            print(f"Ошибка upload_file_to_kaiten: {e}")
            return False
    
    async def upload_file(self, card_id: str, file_data: bytes, 
                          filename: str, content_type: Optional[str] = None) -> dict | None:
        """Загрузить файл в карточку через brain-api (/files/upload/{card_id}).
        Возвращает ответ сервера или None при ошибке."""
        import aiohttp
        try:
            # Сохраняем читаемую кириллическую строку: декодируем percent-encoding и очищаем
            filename = self._sanitize_filename(filename, content_type=content_type)

            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file', file_data, filename=filename, content_type=content_type)
                async with session.post(f"{self.api.base_url}/files/upload/{card_id}", data=data) as resp:
                    status = resp.status
                    if status != 200:
                        return None
                    return await resp.json()
        except Exception as e:
            print(f"Ошибка upload_file: {e}")
            return None

    async def list_files(self, card_id: str) -> dict | None:
        """Список файлов карточки через /files/list/{card_id}"""
        res, status = await self.api.get(f"/files/list/{card_id}")
        if status == 200:
            return res
        return None

    async def download_file(self, file_id: str) -> tuple[bytes | None, int | None]:
        """Скачать файл по file_id через /files/download/{file_id}. Возвращает (bytes, status)"""
        data, status = await self.api.get(f"/files/download/{file_id}", return_bytes=True)
        return data, status

    async def get_file_info(self, file_id: str) -> dict | None:
        res, status = await self.api.get(f"/files/info/{file_id}")
        if status == 200:
            return res
        return None

    async def delete_file(self, file_id: str) -> bool:
        res, status = await self.api.delete(f"/files/delete/{file_id}")
        return status == 200

    async def reorder_files(self, card_id: str, file_ids: list[str]) -> bool:
        res, status = await self.api.post(f"/files/reorder/{card_id}", data={"file_ids": file_ids})
        return status == 200

    async def set_content(self, card_id: str, content: str, client_key: Optional[str] = None) -> bool:
        res, status = await self.api.post("/card/set-content", data={"card_id": card_id, "content": content, "client_key": client_key})
        return status == 200

    async def clear_content(self, card_id: str, client_key: Optional[str] = None) -> bool:
        res, status = await self.api.post("/card/clear-content", data={"card_id": card_id, "client_key": client_key})
        return status == 200

    async def set_client_settings(self, card_id: str, client_id: str, setting_type: str, data: dict) -> tuple[dict | None, int]:
        res, status = await self.api.post("/card/set-client_settings", data={"card_id": card_id, "client_id": client_id, "setting_type": setting_type, "data": data})
        return res, status

    async def add_entity(self, card_id: str, client_id: str, entity_type: str, data: dict, name: Optional[str] = None) -> dict | None:
        res, status = await self.api.post("/card/add-entity", data={"card_id": card_id, "client_id": client_id, "entity_type": entity_type, "data": data, "name": name})
        if status == 200:
            return res
        return None

    async def get_entities(self, card_id: str, client_id: str) -> list[dict] | None:
        res, status = await self.api.get(f"/card/entities?card_id={card_id}&client_id={client_id}")
        if status == 200:
            return res
        return None

    async def get_entity(self, card_id: str, client_id: str, entity_id: str) -> dict | None:
        res, status = await self.api.get(f"/card/entity?card_id={card_id}&client_id={client_id}&entity_id={entity_id}")
        if status == 200:
            return res
        return None

    async def delete_entity(self, card_id: str, client_id: str, entity_id: str) -> tuple[dict | None, int]:
        res, status = await self.api.post("/card/delete-entity", data={"card_id": card_id, "client_id": client_id, "entity_id": entity_id})
        return res, status

    async def update_entity(self, card_id: str, client_id: str, entity_id: str, data: dict, name: Optional[str] = None) -> tuple[dict | None, int]:
        res, status = await self.api.post("/card/update-entity", data={"card_id": card_id, "client_id": client_id, "entity_id": entity_id, "data": data, "name": name})
        return res, status

    def _sanitize_filename(self, filename: str, content_type: Optional[str] = None) -> str:
        """
        Всегда возвращает форматированное имя: <type>_<YYYYMMDD_HHMMSS><ext>
        Сохраняем расширение, если его можно корректно определить из исходного имени,
        иначе пытаемся вывести по Content-Type.
        """
        import re
        import urllib.parse
        from datetime import datetime

        def _ext_from_content_type(ct: Optional[str]) -> str:
            if not ct:
                return ''
            mapping = {
                'image/png': '.png',
                'image/jpeg': '.jpg',
                'image/jpg': '.jpg',
                'image/gif': '.gif',
                'image/webp': '.webp',
                'video/mp4': '.mp4',
                'application/pdf': '.pdf'
            }
            return mapping.get(ct.split(';', 1)[0].strip().lower(), '')

        def _type_label_from_content_type(ct: Optional[str], ext: str) -> str:
            if ct:
                if ct.startswith('image/'):
                    return 'image'
                if ct.startswith('video/'):
                    return 'video'
                if ct == 'application/pdf':
                    return 'document'
                return 'file'
            image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}
            video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
            if ext in image_exts:
                return 'image'
            if ext in video_exts:
                return 'video'
            return 'file'

        # Попытка получить расширение из исходного имени
        ext = ''
        if filename:
            decoded = urllib.parse.unquote(filename)
            if '%' in decoded:
                decoded = urllib.parse.unquote(decoded)
            if '.' in decoded:
                maybe = decoded.rsplit('.', 1)[1].lower()
                if re.match(r'^[a-z0-9]{1,5}$', maybe):
                    ext = '.' + maybe

        if not ext:
            ext = _ext_from_content_type(content_type)

        label = _type_label_from_content_type(content_type, ext)
        ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return f"{label}_{ts}{ext}"
    
    def _is_image_file(self, file_data: bytes, file_name: str) -> bool:
        """Проверяет, является ли файл изображением"""
        # По magic bytes
        if len(file_data) >= 8:
            if file_data[:8] == b'\x89PNG\r\n\x1a\n':
                return True
            if file_data[:2] == b'\xff\xd8':
                return True
            if file_data[:6] in (b'GIF87a', b'GIF89a'):
                return True
            if file_data[:4] == b'RIFF' and len(file_data) >= 12 and file_data[8:12] == b'WEBP':
                return True
            if file_data[:2] == b'BM':
                return True
        
        # По расширению
        if file_name:
            ext = file_name.lower().rsplit('.', 1)[-1] if '.' in file_name else ''
            if ext in ('png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'tiff', 'tif'):
                return True
        
        return False
    
    def _convert_to_png(self, file_data: bytes) -> bytes:
        """Конвертирует изображение в PNG"""
        import io
        from PIL import Image
        
        image = Image.open(io.BytesIO(file_data))
        
        # Конвертируем в RGBA для поддержки прозрачности
        if image.mode not in ('RGBA', 'RGB'):
            if image.mode == 'P':
                image = image.convert('RGBA')
            elif image.mode in ('LA', 'L'):
                image = image.convert('RGBA')
            else:
                image = image.convert('RGBA')
        
        output = io.BytesIO()
        image.save(output, format='PNG', optimize=True)
        return output.getvalue()
    
    async def send_now(self, card_id: str) -> bool:
        """Отправить карточку немедленно (/card/send-now)"""
        res, status = await self.api.post("/card/send-now", data={"card_id": card_id})
        return status == 200

    async def get_busy_slots(self, start: Optional[str] = None, end: Optional[str] = None) -> dict | None:
        """Получить занятые слоты (/time/busy-slots)"""
        params = {}
        if start is not None:
            params['start'] = start
        if end is not None:
            params['end'] = end
        res, status = await self.api.get("/time/busy-slots", params=params)
        if status == 200:
            return res
        return None

    async def get_messages(self, card_id: Optional[str] = None, 
                           message_type: Optional[str] = None) -> dict | None:
        """Получить сообщения карточки (/card/get-messages)"""
        params = {}
        if card_id is not None:
            params['card_id'] = card_id
        if message_type is not None:
            params['message_type'] = message_type
        res, status = await self.api.get("/card/get-messages", params=params)
        if status == 200:
            return res
        return None
    
    async def get_card_by_message_id(self, message_id: int) -> dict | None:
        """Получить карточку по ID сообщения"""
        
        res, status = await self.api.get(f"/card/get-card-by-message_id/{message_id}")
        if status == 200:
            return res
        return None

    def _detect_content_type(self, file_data: bytes, file_name: str) -> str:
        """Определяет content_type файла"""
        # По magic bytes
        if len(file_data) >= 8:
            if file_data[:8] == b'\x89PNG\r\n\x1a\n':
                return 'image/png'
            if file_data[:2] == b'\xff\xd8':
                return 'image/jpeg'
            if file_data[:6] in (b'GIF87a', b'GIF89a'):
                return 'image/gif'
            if file_data[:4] == b'RIFF' and len(file_data) >= 12 and file_data[8:12] == b'WEBP':
                return 'image/webp'
            if file_data[:4] == b'%PDF':
                return 'application/pdf'
            if len(file_data) >= 12 and file_data[4:8] == b'ftyp':
                return 'video/mp4'
        
        # По расширению
        ext_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.pdf': 'application/pdf',
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
        }
        
        if '.' in file_name:
            ext = '.' + file_name.rsplit('.', 1)[1].lower()
            if ext in ext_map:
                return ext_map[ext]
        
        return 'application/octet-stream'


# Создаём инстанс по умолчанию для использования в executors
brain_client = BrainAPIClient()

# Экспортируем методы для обратной совместимости
get_cards = brain_client.get_cards
update_card = brain_client.update_card
get_users = brain_client.get_users
get_user = brain_client.get_user
get_user_role = brain_client.get_user_role
create_user = brain_client.create_user
update_user = brain_client.update_user
delete_user = brain_client.delete_user
insert_scene = brain_client.insert_scene
load_scene = brain_client.load_scene
update_scene = brain_client.update_scene
delete_scene = brain_client.delete_scene
get_all_scenes = brain_client.get_all_scenes
add_editor_note = brain_client.add_editor_note
change_card_status = brain_client.change_card_status
get_kaiten_users = brain_client.get_kaiten_users
get_kaiten_users_dict = brain_client.get_kaiten_users_dict
get_kaiten_files = brain_client.get_kaiten_files
upload_file_to_kaiten = brain_client.upload_file_to_kaiten
upload_files_to_card = brain_client.upload_files_to_card
notify_executor = brain_client.notify_executor

# Files
upload_file = brain_client.upload_file
list_files = brain_client.list_files
download_file = brain_client.download_file
get_file_info = brain_client.get_file_info
delete_file = brain_client.delete_file
reorder_files = brain_client.reorder_files

# Content & entities
set_content = brain_client.set_content
clear_content = brain_client.clear_content
set_client_settings = brain_client.set_client_settings
add_entity = brain_client.add_entity
get_entities = brain_client.get_entities
get_entity = brain_client.get_entity
delete_entity = brain_client.delete_entity
update_entity = brain_client.update_entity

# Misc
send_now = brain_client.send_now
get_busy_slots = brain_client.get_busy_slots

# Messages
get_messages = brain_client.get_messages
get_card_by_message_id = brain_client.get_card_by_message_id