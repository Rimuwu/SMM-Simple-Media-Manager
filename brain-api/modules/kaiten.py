from typing import Any, Optional
from global_modules.kaiten_client import KaitenClient
from os import getenv

TOKEN = getenv("KAITEN_TOKEN", '')
DOMAIN = getenv("KAITEN_DOMAIN", "kaiten.io")
kaiten = KaitenClient(token=TOKEN, domain=DOMAIN)

async def add_kaiten_comment(task_id: int, text: str):
    """
    Добавляет комментарий к карточке в Kaiten.
    """
    if not task_id:
        return

    try:
        async with kaiten as client:
            await client.add_comment(task_id, text)
    except Exception as e:
        print(f"Error adding comment to Kaiten task {task_id}: {e}")

async def update_kaiten_card_field(
    task_id: int, 
    field: str, 
    value: Any, 
    comment: Optional[str] = None
    ):
    """
    Обновляет поле карточки в Kaiten и опционально добавляет комментарий.
    """
    if not task_id:
        return

    try:
        async with kaiten as client:
            kwargs = {field: value}
            await client.update_card(task_id, **kwargs)

            if comment:
                await client.add_comment(task_id, comment)
    except Exception as e:
        print(
            f"Ошибка обновления карточки Kaiten {task_id} ({field}): {e}"
            )

async def get_kaiten_user_name(
    tasker_id: int) -> str | None:
    """
    Получает имя пользователя из Kaiten
    """

    try:
        async with kaiten as client:
            users = await client.get_company_users(
                only_virtual=True)

            kaiten_user = next(
                (u for u in users if u['id'] == tasker_id
                    ), None)

            if kaiten_user:
                return kaiten_user['full_name']

    except Exception as e:
        print(f"Ошибка получения имени пользователя Kaiten: {e}")

    return None