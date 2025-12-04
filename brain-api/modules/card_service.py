from datetime import datetime
from typing import Optional
from models.User import User
from modules.api_client import executors_api
from modules.kaiten import kaiten
from modules.constants import ApiEndpoints

async def notify_executor(executor_id: str, message: str):
    """
    Отправляет уведомление исполнителю в Telegram.
    """
    try:
        executor = await User.get_by_key('user_id', executor_id)
        if executor:
            await executors_api.post(
                ApiEndpoints.NOTIFY_USER,
                data={
                    "user_id": executor.telegram_id,
                    "message": message
                }
            )
    except Exception as e:
        print(f"Error notifying executor {executor_id}: {e}")

async def get_kaiten_user_name(user: User) -> str:
    """
    Получает имя пользователя из Kaiten или использует telegram_id/full_name.
    """
    if user.tasker_id:
        try:
            async with kaiten as client:
                users = await client.get_company_users(only_virtual=True)
                # Ищем пользователя по ID
                kaiten_user = next((u for u in users if u['id'] == user.tasker_id), None)
                if kaiten_user:
                    return kaiten_user['full_name']
        except Exception as e:
            print(f"Error getting Kaiten user name: {e}")
    
    return f"@{user.telegram_id}"

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

async def update_kaiten_card_field(task_id: int, field: str, value: any, comment: Optional[str] = None):
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
        print(f"Error updating Kaiten card {task_id} ({field}): {e}")
