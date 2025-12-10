import asyncio
import importlib
from datetime import datetime, timedelta
from typing import Callable, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from models.ScheduledTask import ScheduledTask
from models.Card import Card
from global_modules.timezone import now_naive as moscow_now
from modules.logs import brain_logger as logger

# logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    Планировщик для выполнения запланированных задач.
    
    Работает в фоновом режиме и проверяет задачи каждые N секунд.
    """
    
    def __init__(self, session_factory: Callable, check_interval: int = 10):
        """
        Args:
            session_factory: Фабрика для создания сессий БД
            check_interval: Интервал проверки задач в секундах (по умолчанию 10)
        """
        self.session_factory = session_factory
        self.check_interval = check_interval
        self.is_running = False

    async def start(self):
        """Запустить планировщик."""
        self.is_running = True
        logger.info("Планировщик задач запущен")
        
        while self.is_running:
            try:
                await self._check_and_execute_tasks()
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}", exc_info=True)
            
            await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        """Остановить планировщик."""
        self.is_running = False
        logger.info("Планировщик задач остановлен")
    
    async def _check_and_execute_tasks(self):
        """Проверить и выполнить задачи, время которых наступило."""
        async with self.session_factory() as session:
            # Получаем все задачи, время выполнения которых уже наступило
            query = select(ScheduledTask).where(
                ScheduledTask.execute_at <= moscow_now()
            )
            result = await session.execute(query)
            tasks = result.scalars().all()
            
            for task in tasks:
                await self._execute_task(task, session)
    
    async def _execute_task(self, 
                            task: ScheduledTask, session: AsyncSession):
        """
        Выполнить задачу.
        
        Args:
            task: Задача для выполнения
            session: Сессия БД
        """
        try:
            logger.info(f"Выполнение задачи {task.task_id}: {task.function_path}")
            
            # Импортируем функцию по пути
            func = self._import_function(task.function_path)
            
            # Получаем карточку, если card_id указан в аргументах
            if 'card_id' in task.arguments:
                card = await session.get(Card, task.arguments['card_id'])
                if not card:
                    logger.error(f"Карточка {task.arguments['card_id']} не найдена")
                    await session.delete(task)
                    await session.commit()
                    return

                # Добавляем карточку в аргументы
                task.arguments['card'] = card

            # Удаляем задачу до выполнения, чтобы избежать повторного выполнения
            await session.delete(task)
            await session.commit()

            # Выполняем функцию
            if asyncio.iscoroutinefunction(func):
                await func(**task.arguments)
            else:
                func(**task.arguments)

            logger.info(f"Задача {task.task_id} выполнена успешно")

        except Exception as e:
            logger.error(f"Ошибка выполнения задачи {task.task_id}: {e}", exc_info=True)
            await session.delete(task)
            await session.commit()

    def _import_function(self, function_path: str) -> Callable:
        """
        Импортировать функцию по её пути.
        
        Args:
            function_path: Путь к функции в формате "module.submodule.function_name"
            
        Returns:
            Функция для выполнения
            
        Raises:
            ImportError: Если модуль или функция не найдены
        """
        try:
            module_path, function_name = function_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            return getattr(module, function_name)
        except (ValueError, ImportError, AttributeError) as e:
            logger.error(f"Не удалось импортировать функцию {function_path}: {e}")
            raise


async def create_scheduled_task(
    session: AsyncSession,
    function_path: str,
    execute_at: datetime,
    **kwargs
) -> ScheduledTask:
    """
    Создать запланированную задачу.
    
    Args:
        session: Сессия БД
        function_path: Путь к функции для выполнения
        execute_at: Время выполнения задачи
        **kwargs: Аргументы для функции
        
    Returns:
        Созданная задача
        
    Example:
        task = await create_scheduled_task(
            session=session,
            function_path="modules.notifications.send_card_reminder",
            execute_at=datetime(2025, 11, 28, 10, 0, 0),
            card_id="uuid-string",
            message_type="reminder"
        )
    """
    task = ScheduledTask(
        function_path=function_path,
        execute_at=execute_at,
        arguments=kwargs
    )
    
    session.add(task)
    await session.commit()
    await session.refresh(task)
    
    logger.info(f"Создана задача {task.task_id} для выполнения в {execute_at}")
    
    return task


async def schedule_card_notifications(
    session: AsyncSession, card: Card) -> None:
    """
    Запланировать уведомления для карточки.
    Создает задачи:
    - За 2 дня до дедлайна: напоминание исполнителю (если статус не ready)
    - За 1 день до дедлайна: уведомление админам если нет исполнителя
    
    Args:
        session: Сессия БД
        card: Карточка для которой нужно запланировать уведомления
    """
    if not card.deadline:
        logger.info(f"У карточки {card.card_id} нет дедлайна, задачи не создаются")
        return
    
    from datetime import timedelta
    from uuid import UUID as PyUUID
    
    # Вычисляем время для уведомлений
    two_days_before = card.deadline - timedelta(days=2)
    one_day_before = card.deadline - timedelta(days=1)
    
    # Проверяем, что время уведомлений еще не прошло
    now = moscow_now()
    
    card_uuid = card.card_id if isinstance(card.card_id, PyUUID) else PyUUID(str(card.card_id))
    
    # Задача: напоминание исполнителю за 2 дня
    if two_days_before > now:
        task = ScheduledTask(
            card_id=card_uuid,
            function_path="modules.notifications.send_card_deadline_reminder",
            execute_at=two_days_before,
            arguments={"card_id": str(card.card_id)}
        )
        session.add(task)
        logger.info(f"Создана задача напоминания для карточки {card.card_id} на {two_days_before}")
    
    # Задача: уведомление админам за 1 день (только если дедлайн больше чем через 1 день)
    time_until_deadline = (card.deadline - now).total_seconds()
    if one_day_before > now and time_until_deadline > 86400:  # 86400 секунд = 1 день
        task = ScheduledTask(
            card_id=card_uuid,
            function_path="modules.notifications.send_admin_no_executor_alert",
            execute_at=one_day_before,
            arguments={"card_id": str(card.card_id)}
        )
        session.add(task)
        logger.info(f"Создана задача уведомления админов для карточки {card.card_id} на {one_day_before}")
    
    # Задача: уведомление на форум о просроченном дедлайне (в момент дедлайна)
    if card.deadline > now:
        task = ScheduledTask(
            card_id=card_uuid,
            function_path="modules.notifications.send_forum_deadline_passed",
            execute_at=card.deadline,
            arguments={"card_id": str(card.card_id)}
        )
        session.add(task)
        logger.info(f"Создана задача уведомления о дедлайне для карточки {card.card_id} на {card.deadline}")

    await session.commit()


async def cancel_card_tasks(
    session: AsyncSession, card_id: str) -> int:
    """
    Отменить все запланированные задачи для карточки.
    
    Args:
        session: Сессия БД
        card_id: ID карточки (строка или UUID)
        
    Returns:
        Количество удаленных задач
    """
    from sqlalchemy import delete
    from uuid import UUID as PyUUID
    
    # Преобразуем card_id в UUID если это строка
    try:
        card_uuid = PyUUID(card_id) if isinstance(card_id, str) else card_id
    except ValueError:
        logger.error(f"Невалидный card_id: {card_id}")
        return 0
    
    # Находим все задачи, связанные с этой карточкой
    stmt = delete(ScheduledTask).where(
        ScheduledTask.card_id == card_uuid
    )
    
    result = await session.execute(stmt)
    await session.commit()
    
    deleted_count = result.rowcount
    logger.info(f"Удалено {deleted_count} задач для карточки {card_id}")
    
    return deleted_count


async def reschedule_card_notifications(session: AsyncSession, card: Card) -> None:
    """
    Перепланировать уведомления для карточки при изменении дедлайна.
    Удаляет старые задачи и создает новые с обновленным временем.
    
    Args:
        session: Сессия БД
        card: Карточка с обновленным дедлайном
    """
    # Удаляем старые задачи
    deleted_count = await cancel_card_tasks(session, str(card.card_id))
    logger.info(f"Удалено {deleted_count} старых задач для карточки {card.card_id}")
    
    # Создаем новые задачи
    await schedule_card_notifications(session, card)
    logger.info(f"Созданы новые задачи для карточки {card.card_id}")


# ================== Функции для управления тасками публикации ==================


async def schedule_post_tasks(session: AsyncSession, card: Card) -> None:
    """
    Запланировать задачи публикации постов для карточки.
    Создает задачи для каждого канала (клиента) карточки.
    
    Args:
        session: Сессия БД
        card: Карточка для публикации
    """
    from global_modules.json_get import open_clients
    from uuid import UUID as PyUUID
    
    if not card.send_time:
        logger.info(f"У карточки {card.card_id} не указано время отправки")
        return
    
    if not card.clients:
        logger.info(f"У карточки {card.card_id} нет каналов для публикации")
        return
    
    clients = open_clients() or {}
    now = moscow_now()
    
    card_uuid = card.card_id if isinstance(card.card_id, PyUUID) else PyUUID(str(card.card_id))
    
    for client_key in card.clients:
        client_config = clients.get(client_key)
        if not client_config:
            logger.warning(f"Клиент {client_key} не найден в конфигурации")
            continue
        
        executor_name = client_config.get('executor_name') or client_config.get('executor')
        if not executor_name:
            logger.warning(f"У клиента {client_key} не указан исполнитель")
            continue
        
        # Создаем задачу на отправку в указанное время
        if card.send_time > now:
            send_task = ScheduledTask(
                card_id=card_uuid,
                function_path="modules.notifications.send_post_now",
                execute_at=card.send_time,
                arguments={
                    "card_id": str(card.card_id),
                    "client_key": client_key
                }
            )
            session.add(send_task)
            logger.info(f"Создана задача отправки поста для {client_key} на {card.send_time}")
        else:
            # Время уже прошло - отправляем сейчас
            send_task = ScheduledTask(
                card_id=card_uuid,
                function_path="modules.notifications.send_post_now",
                execute_at=now + timedelta(seconds=5),
                arguments={
                    "card_id": str(card.card_id),
                    "client_key": client_key
                }
            )
            session.add(send_task)
            logger.info(f"Время отправки прошло, создана задача немедленной отправки для {client_key}")
    
    # Создаём задачу финализации после отправки всех постов
    # Выполняется через 2 минуты после последнего поста
    finalize_time = (card.send_time if card.send_time > now else now) + timedelta(minutes=2)
    finalize_task = ScheduledTask(
        card_id=card_uuid,
        function_path="modules.notifications.finalize_card_publication",
        execute_at=finalize_time,
        arguments={"card_id": str(card.card_id)}
    )
    session.add(finalize_task)
    logger.info(f"Создана задача финализации публикации для карточки {card.card_id} на {finalize_time}")
    
    await session.commit()


async def cancel_post_tasks(session: AsyncSession, card_id: str) -> int:
    """
    Отменить все задачи публикации постов для карточки.
    Удаляет только задачи, связанные с публикацией (schedule_post, send_post, verify_post).
    
    Args:
        session: Сессия БД
        card_id: ID карточки
        
    Returns:
        Количество удаленных задач
    """
    from sqlalchemy import delete, or_
    from uuid import UUID as PyUUID
    
    try:
        card_uuid = PyUUID(card_id) if isinstance(card_id, str) else card_id
    except ValueError:
        logger.error(f"Невалидный card_id: {card_id}")
        return 0
    
    # Удаляем задачи публикации и финализации
    post_functions = [
        "modules.notifications.send_post_now",
        "modules.notifications.finalize_card_publication",
    ]
    
    stmt = delete(ScheduledTask).where(
        ScheduledTask.card_id == card_uuid,
        or_(*[ScheduledTask.function_path == func for func in post_functions])
    )
    
    result = await session.execute(stmt)
    await session.commit()
    
    deleted_count = result.rowcount
    logger.info(f"Удалено {deleted_count} задач публикации для карточки {card_id}")
    
    return deleted_count


async def reschedule_post_tasks(session: AsyncSession, card: Card) -> None:
    """
    Перепланировать задачи публикации при изменении времени отправки.
    Удаляет старые задачи публикации и создает новые.
    
    Args:
        session: Сессия БД
        card: Карточка с обновленным временем отправки
    """
    # Удаляем старые задачи публикации
    deleted_count = await cancel_post_tasks(session, str(card.card_id))
    logger.info(f"Удалено {deleted_count} старых задач публикации для карточки {card.card_id}")
    
    # Создаем новые задачи только если статус ready
    from global_modules.classes.enums import CardStatus
    if card.status == CardStatus.ready:
        await schedule_post_tasks(session, card)
        logger.info(f"Созданы новые задачи публикации для карточки {card.card_id}")


async def update_post_tasks_time(session: AsyncSession, card: Card, new_time: datetime) -> int:
    """
    Обновить время выполнения существующих задач публикации.
    Используется для кнопки "Отправить сейчас" - не удаляет/создаёт, а меняет время.
    
    Args:
        session: Сессия БД
        card: Карточка
        new_time: Новое время выполнения
        
    Returns:
        Количество обновлённых задач
    """
    from sqlalchemy import update, or_
    from uuid import UUID as PyUUID
    
    try:
        card_uuid = card.card_id if isinstance(card.card_id, PyUUID) else PyUUID(str(card.card_id))
    except ValueError:
        logger.error(f"Невалидный card_id: {card.card_id}")
        return 0
    
    # Обновляем время для задач публикации
    post_functions = [
        "modules.notifications.send_post_now",
    ]
    
    stmt = (
        update(ScheduledTask)
        .where(
            ScheduledTask.card_id == card_uuid,
            or_(*[ScheduledTask.function_path == func for func in post_functions])
        )
        .values(execute_at=new_time)
    )
    
    result = await session.execute(stmt)
    
    # Также обновляем задачу финализации на время + 2 минуты
    finalize_time = new_time + timedelta(minutes=2)
    
    finalize_stmt = (
        update(ScheduledTask)
        .where(
            ScheduledTask.card_id == card_uuid,
            ScheduledTask.function_path == "modules.notifications.finalize_card_publication"
        )
        .values(execute_at=finalize_time)
    )
    await session.execute(finalize_stmt)
    
    await session.commit()
    
    updated_count = result.rowcount
    logger.info(f"Обновлено время для {updated_count} задач публикации карточки {card.card_id} на {new_time}")
    
    return updated_count
