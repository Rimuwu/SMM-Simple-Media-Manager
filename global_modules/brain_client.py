"""
Клиент для работы с brain-api.
Предоставляет типизированные wrapper-функции для API запросов.

Используется в executors и других сервисах для взаимодействия с brain-api.
"""
from typing import Optional
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

    async def update_card(
        self,
        card_id: str,
        status: Optional[CardStatus] = None,
        executor_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        need_check: Optional[bool] = None,
        need_send: Optional[bool] = None,
        forum_message_id: Optional[int] = None,
        content: Optional[str] = None,
        clients: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        deadline: Optional[str] = None,
        image_prompt: Optional[str] = None,
        prompt_sended: Optional[bool] = None,
        prompt_message: Optional[int] = None,
        calendar_id: Optional[str] = None,
        send_time: Optional[str] = None,
        post_images: Optional[list[str]] = None
    ) -> dict | None:
        """Обновить карточку"""
        data = {
            "card_id": card_id,
            "status": status.value if status else None,
            "executor_id": executor_id,
            "customer_id": customer_id,
            "need_check": need_check,
            "need_send": need_send,
            "forum_message_id": forum_message_id,
            "content": content,
            "clients": clients,
            "tags": tags,
            "deadline": deadline,
            "send_time": send_time,
            "image_prompt": image_prompt,
            "prompt_sended": prompt_sended,
            "prompt_message": prompt_message,
            "calendar_id": calendar_id,
            "post_images": post_images
        }
        
        card, res_status = await self.api.post("/card/update", data=data)

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

    # ==================== Пользователи ====================
    
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


# Создаём инстанс по умолчанию для использования в executors
brain_client = BrainAPIClient()

# Экспортируем методы для обратной совместимости
get_cards = brain_client.get_cards
update_card = brain_client.update_card
get_users = brain_client.get_users
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
get_kaiten_users = brain_client.get_kaiten_users
get_kaiten_users_dict = brain_client.get_kaiten_users_dict
get_kaiten_files = brain_client.get_kaiten_files
