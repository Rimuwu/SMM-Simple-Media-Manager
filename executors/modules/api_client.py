from typing import Optional
from global_modules.api_client import APIClient
from global_modules.classes.enums import CardStatus, Department

brain_api = APIClient('http://brain:8000')

async def get_user_role(telegram_id: int) -> str | None:
    """Получить роль пользователя по telegram_id"""
    user, status_code = await brain_api.get(f"/user/get",
                        params={"telegram_id": telegram_id})
    if status_code == 200 and user:
        return user[0]['role']
    return None

async def get_cards(task_id: Optional[str] = None, 
              card_id: Optional[str] = None, 
              status: Optional[CardStatus] = None,
              customer_id: Optional[str] = None,
              executor_id: Optional[str] = None,
              need_check: Optional[bool] = None,
              forum_message_id: Optional[int] = None
              ):

    """Получить карточки по различным параметрам"""
    params = {
        "task_id": task_id,
        "card_id": card_id,
        "status": status,
        "customer_id": customer_id,
        "executor_id": executor_id,
        "need_check": need_check,
        "forum_message_id": forum_message_id
    }
    cards, res_status = await brain_api.get(
        "/card/get",
        params=params
    )

    if res_status != 200:
        return []

    return cards

async def update_card(card_id: str,
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
                      post_images: Optional[list[str]] = None  # Список имён файлов из Kaiten
                      ):
    """
    Обновить карточку
    """
    data = {
        "card_id": card_id,
        "status": status,
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
    
    card, res_status = await brain_api.post(
        f"/card/update",
        data=data
    )

    if res_status != 200:
        return None

    return card


async def get_users(
                   telegram_id: Optional[int] = None,
                   tasker_id: Optional[int] = None,
                   role: Optional[str] = None,
                   user_id: Optional[str] = None,
                   department: Optional[str] = None
                   ):
    """Получить пользователей по различным параметрам"""
    params = {
        "telegram_id": telegram_id,
        "tasker_id": tasker_id,
        "role": role,
        "user_id": user_id,
        "department": department
    }
    users, res_status = await brain_api.get(
        "/user/get",
        params=params
    )

    if res_status != 200:
        return []

    return users

async def update_user(telegram_id: int,
                      role: Optional[str] = None,
                      tasker_id: Optional[int] = None,
                      department: Optional[Department] = None,
                      about: Optional[str] = None
                      ):
    """Обновить пользователя"""
    data = {
        "telegram_id": telegram_id,
        "role": role,
        "tasker_id": tasker_id,
        "department": department,
        "about": about
    }
    user, res_status = await brain_api.post(
        f"/user/update",
        data=data
    )

    if res_status != 200:
        return None

    return user


# ===== Работа со сценами =====

async def insert_scene(user_id: int, data: dict) -> bool:
    """Создание новой сцены в БД"""
    scene_data = {
        "user_id": user_id,
        "scene": data.get("scene"),
        "scene_path": data.get("scene_path"),
        "page": data.get("page"),
        "message_id": data.get("message_id"),
        "data": data.get("data")
    }
    
    scene, res_status = await brain_api.post(
        "/scene/create",
        data=scene_data
    )
    
    return res_status == 200 and scene is not None


async def load_scene(user_id: int) -> dict | None:
    """Загрузка сцены пользователя из БД"""
    scene, res_status = await brain_api.get(
        f"/scene/get/{user_id}"
    )
    
    if res_status == 200 and scene:
        return scene
    
    return None


async def update_scene(user_id: int, data: dict) -> bool:
    """Обновление сцены в БД"""
    scene_data = {
        "user_id": user_id,
        "scene": data.get("scene"),
        "scene_path": data.get("scene_path"),
        "page": data.get("page"),
        "message_id": data.get("message_id"),
        "data": data.get("data")
    }
    
    scene, res_status = await brain_api.post(
        "/scene/update",
        data=scene_data
    )
    
    return res_status == 200 and scene is not None


async def delete_scene(user_id: int) -> bool:
    """Удаление сцены пользователя из БД"""
    result, res_status = await brain_api.delete(
        f"/scene/delete/{user_id}"
    )
    
    return res_status == 200

async def get_all_scenes() -> list[dict]:
    """Получить все сцены из БД"""
    scenes, res_status = await brain_api.get(
        "/scene/get-all"
    )
    
    if res_status == 200 and scenes:
        return scenes

    return []

async def create_user(telegram_id: int, 
                      role: str, 
                      tasker_id: Optional[int] = None,
                      department: Optional[str] = None,
                      about: Optional[str] = None):
    data = {
        "telegram_id": telegram_id,
        "role": role,
        "tasker_id": tasker_id,
        "department": department,
        "about": about
    }
    user, res_status = await brain_api.post("/user/create", data=data)
    if res_status == 201 or res_status == 200:
        return user
    return None

async def delete_user(telegram_id: int):
    return await brain_api.delete(f"/user/delete?telegram_id={telegram_id}")

async def get_kaiten_users(only_virtual: bool = True):
    """Получить пользователей из Kaiten с кешированием"""
    params = {'only_virtual': 1 if only_virtual else 0}
    kaiten_users_list, status = await brain_api.get(
        '/kaiten/get-users',
        params=params,
        use_cache=True
    )
    
    if status == 200 and kaiten_users_list:
        return kaiten_users_list
    
    return []

async def get_kaiten_users_dict(only_virtual: bool = True):
    """Получить словарь пользователей из Kaiten {id: full_name} с кешированием"""
    kaiten_users_list = await get_kaiten_users(only_virtual)
    return {user['id']: user['full_name'] for user in kaiten_users_list}

async def get_kaiten_files(task_id: str):
    """Получить файлы задачи из Kaiten с кешированием"""
    response, status = await brain_api.get(
        f"/kaiten/get-files/{task_id}",
        use_cache=False
    )
    
    if status == 200 and response:
        return response
    
    return None

async def add_editor_note(card_id: str, content: str, author_user_id: str):
    """Добавить комментарий редактора к карточке"""
    data = {
        "card_id": card_id,
        "content": content,
        "author": author_user_id
    }
    
    result, status = await brain_api.post(
        "/card/add-editor-note",
        data=data
    )
    
    if status == 200:
        return result
    
    return None