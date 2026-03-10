
from typing import Optional
from uuid import UUID as _UUID
from datetime import datetime

from models.User import User
from app.models.task.TaskFile import CardFile
from app.models.card.ClientSetting import ClientSetting
from modules.enums import CardStatus
from app.modules.components.logs import logger

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.card.Card import Card
    from app.models.task.Task import Task

async def increment_reviewers_tasks(card: 'Card'):
    """
    Увеличивает счётчик tasks_checked для заказчика задания (если он админ).
    """
    try:
        task = await card.get_task()
        if task and task.customer_id:
            customer = await User.get_by_key('user_id', task.customer_id)
            if customer and customer.role == 'admin':
                await customer.update(tasks_checked=customer.tasks_checked + 1)
                logger.info(f"Увеличен счётчик проверенных задач у {customer.user_id}")
    except Exception as e:
        logger.error(f"Ошибка увеличения счётчика: {e}")


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



async def create_task(
    title: str,
    description: str = "",
    deadline=None,
    customer_id=None,
    executor_id=None,
) -> "Optional[Task]":
    """Создать задание (контейнер для нескольких постов/карточек)."""
    from app.models.task.Task import Task
    try:
        task = await Task.create(
            name=title,
            description=description or None,
            deadline=datetime.fromisoformat(str(deadline)) if deadline else None,
            customer_id=_UUID(str(customer_id)) if customer_id else None,
            executor_id=_UUID(str(executor_id)) if executor_id else None,
        )
        return task
    except Exception as e:
        logger.error(f"create_task error: {e}")
        return None


async def create_card(
    title: str,
    description: str = "",
    send_time=None,
    channels: list | None = None,
    tags: list | None = None,
    need_check: bool = True,
    image_prompt: Optional[str] = None,
    type_id=None,
    task_id=None,
    **kwargs,
) -> Optional['Card']:
    """Создать карточку с полными сайд-эффектами.

    Создаёт запись ``ClientSetting`` для каждого канала и отправляет
    сообщение на форум, если тип задачи публичный.
    """
    from modules.exec.executors_client import send_forum_message
    from app.models.card.Card import Card

    try:
        card = await Card.create(
            name=title,
            description=description,
            clients=channels or [],
            tags=tags or [],
            send_time=datetime.fromisoformat(str(send_time)) if send_time else None,
            image_prompt=image_prompt,
            need_check=need_check,
            task_id=_UUID(str(task_id)) if task_id else None,
        )
        for key in channels or []:
            try:
                await ClientSetting.create(card_id=card.card_id, client_key=str(key), data={})
            except Exception:
                pass

        is_public = str(type_id) in ("public", "CardType.public", "1")
        if is_public:
            await send_forum_message(str(card.card_id))

        return card
    except Exception as e:
        logger.error(f"create_card error: {e}")
        return None


async def destroy_card(card_id: str) -> bool:
    """Удалить карточку с каскадной очисткой файлов, сообщений и календаря."""
    from app.models.Message import CardMessage
    from modules.exec.executors_client import (
        delete_forum_message_by_id,
        delete_all_complete_previews,
    )
    from modules.calendar.calendar import delete_calendar_event
    from app.models.card.Card import Card

    try:
        card = await Card.get_by_id(_UUID(str(card_id)))
        if not card:
            return False

        files = await CardFile.filter_by(card_id=card.card_id)
        for f in files:
            await f.delete()

        messages = await CardMessage.filter_by(card_id=card.card_id)
        forum_msgs = [m for m in messages if m.message_type == "forum"]
        complete_msgs = [m for m in messages if "complete" in (m.message_type or "")]

        for msg in forum_msgs:
            await delete_forum_message_by_id(msg.message_id)
        await delete_all_complete_previews(
            [m.message_id for m in complete_msgs if "info" in m.message_type]
        )
        for msg in messages:
            await msg.delete()

        if card.calendar_id:
            try:
                await delete_calendar_event(card.calendar_id)
            except Exception:
                pass

        await card.delete()
        return True
    except Exception as e:
        logger.error(f"destroy_card error: {e}")
        return False


async def change_card_status(
    card_id: str,
    status: CardStatus,
    who_changed: str = "admin",
    comment=None,
) -> Optional['Card']:
    """Сменить статус карточки через соответствующий обработчик статуса."""
    from modules.card import status_changers
    from app.models.card.Card import Card, CardStatus

    try:
        card = await Card.get_by_id(_UUID(str(card_id)))
        if not card:
            return None

        handler = {
            CardStatus.pass_: status_changers.to_pass,
            CardStatus.edited: status_changers.to_edited,
            CardStatus.review: status_changers.to_review,
            CardStatus.ready: status_changers.to_ready,
            CardStatus.sent: status_changers.to_sent,
        }.get(status)

        if handler:
            await handler(card=card, who_changed=who_changed)
        else:
            await card.update(status=status)

        return card
    except Exception as e:
        logger.error(f"change_card_status error: {e}")
        return None