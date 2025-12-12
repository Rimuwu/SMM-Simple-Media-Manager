
from typing import Optional
from models.User import User
from models.Card import Card
from modules.api_client import executors_api
from modules.constants import ApiEndpoints
from modules.logs import brain_logger as logger


async def increment_reviewers_tasks(card: Card):
    """
    Увеличивает счётчик tasks_checked для всех редакторов,
    которые оставили комментарии в editor_notes (не is_customer).
    """
    if not card.editor_notes:
        return

    try:
        if card.editor_id:
            editor = await User.get_by_key(
                'user_id', card.editor_id
            )
        elif card.customer_id:
            editor = await User.get_by_key(
                'user_id', card.customer_id
            )
            if editor and editor.role != 'admin':
                editor = None
        else:
            editor = None

        if editor:
            await editor.update(
                tasks_checked=editor.tasks_checked + 1)
            logger.info(f"Увеличен счётчик проверенных задач у {editor.user_id}")
    except Exception as e:
        logger.error(f"Ошибка увеличения счётчика созданных задач: {e}")


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