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
        need_check: Optional[bool] = None,
        forum_message_id: Optional[int] = None
    ) -> list[dict]:
        """Получить карточки по различным параметрам"""
        params = {
            "task_id": task_id,
            "card_id": card_id,
            "status": status.value if status else None,
            "customer_id": customer_id,
            "executor_id": executor_id,
            "need_check": need_check,
            "forum_message_id": forum_message_id
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
        forum_message_id: Optional[int | Nothing] = '__nothing__',
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
            "forum_message_id": forum_message_id,
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
        author_user_id: str
    ) -> dict | None:
        """Добавить комментарий редактора к карточке"""
        data = {
            "card_id": card_id,
            "content": content,
            "author": author_user_id
        }
        
        result, status = await self.api.post("/card/add-editor-note", data=data)
        
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
                
                # Определяем нужно ли конвертировать в PNG
                from modules.file_utils import is_image_by_mime_or_extension
                is_image = file_type == 'photo' or is_image_by_mime_or_extension(mime_type, file_name)
                
                # Загружаем файл
                success = await self.upload_file_to_kaiten(
                    card_id=card_id,
                    file_data=file_content,
                    file_name=file_name,
                    convert_to_png=is_image
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
            file_name = self._sanitize_filename(file_name)
            
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
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Нормализует имя файла для безопасной передачи.
        Если имя содержит не-ASCII символы - заменяет на стандартное.
        """
        import re
        import time
        
        if not filename:
            return f'file_{int(time.time())}'
        
        # Получаем расширение
        if '.' in filename:
            name_part, ext = filename.rsplit('.', 1)
            ext = '.' + ext.lower()
        else:
            name_part = filename
            ext = ''
        
        # Проверяем, содержит ли имя не-ASCII символы
        if not name_part.isascii():
            # Определяем тип файла по расширению
            image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}
            video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
            
            timestamp = int(time.time())
            if ext in image_exts:
                return f'photo_{timestamp}{ext}'
            elif ext in video_exts:
                return f'video_{timestamp}{ext}'
            else:
                return f'file_{timestamp}{ext}'
        
        # Заменяем опасные символы для файловой системы
        name_part = re.sub(r'[<>:"/\\|?*]', '_', name_part)
        
        # Убираем множественные пробелы и подчёркивания
        name_part = re.sub(r'[\s_]+', '_', name_part)
        
        # Убираем точки в начале (скрытые файлы)
        name_part = name_part.lstrip('.')
        
        # Ограничиваем длину
        max_name_len = 200 - len(ext)
        if len(name_part) > max_name_len:
            name_part = name_part[:max_name_len]
        
        result = name_part + ext
        return result if result and result != ext else f'file_{int(time.time())}{ext}'
    
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
