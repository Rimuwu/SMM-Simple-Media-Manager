from datetime import datetime
from typing import Optional
from models.User import User
from models.Card import Card
from modules.api_client import executors_api
from modules.kaiten import kaiten
from modules.constants import ApiEndpoints
from modules.logs import brain_logger as logger


async def increment_reviewers_tasks(card: Card):
    """
    Увеличивает счётчик tasks_checked для всех редакторов,
    которые оставили комментарии в editor_notes (не is_customer).
    """
    if not card.editor_notes:
        return
    
    # Собираем уникальных авторов комментариев (не заказчиков)
    reviewer_ids = set()
    for note in card.editor_notes:
        if not note.get('is_customer', False):
            author_id = note.get('author')
            if author_id:
                reviewer_ids.add(str(author_id))
    
    # Увеличиваем счётчики для каждого редактора
    for reviewer_id in reviewer_ids:
        try:
            reviewer = await User.get_by_key('user_id', reviewer_id)
            if reviewer:
                await reviewer.update(tasks_checked=reviewer.tasks_checked + 1)
                logger.info(f"Увеличен счётчик проверенных задач для редактора {reviewer.user_id}")
        except Exception as e:
            logger.error(f"Ошибка увеличения счётчика проверенных задач для {reviewer_id}: {e}")


async def increment_customer_tasks(customer_id: str):
    """
    Увеличивает счётчик созданных задач у заказчика.
    """
    if not customer_id:
        return
    
    try:
        customer = await User.get_by_key('user_id', customer_id)
        if customer:
            await customer.update(tasks_created=customer.tasks_created + 1)
            logger.info(f"Увеличен счётчик созданных задач для заказчика {customer.user_id}")
    except Exception as e:
        logger.error(f"Ошибка увеличения счётчика созданных задач: {e}")

async def notify_executor(
    executor_id: str, 
    message: str, 
    task_id: Optional[str] = None, 
    skip_if_page: Optional[str] = None
    ):
    """
    Отправляет уведомление исполнителю в Telegram.
    """
    try:
        executor = await User.get_by_key('user_id', executor_id)
        if executor:
            data = {
                "user_id": executor.telegram_id,
                "message": message
            }
            if task_id:
                data["task_id"] = task_id
            if skip_if_page:
                data["skip_if_page"] = skip_if_page

            await executors_api.post(
                ApiEndpoints.NOTIFY_USER,
                data=data
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
                kaiten_user = next(
                    (u for u in users if u['id'] == user.tasker_id
                     ), None)
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

async def update_kaiten_card_field(
    task_id: int, 
    field: str, 
    value: any, 
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
            f"Error updating Kaiten card {task_id} ({field}): {e}"
            )
