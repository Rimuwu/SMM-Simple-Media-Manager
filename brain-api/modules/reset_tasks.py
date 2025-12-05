"""
Модуль для управления задачами сброса статистики.

При старте API проверяет наличие задач сброса месячной и годовой статистики.
Если задачи отсутствуют, создаёт их на следующее 1-е число.
"""

from datetime import datetime
from uuid import uuid4
from models.ScheduledTask import ScheduledTask
from global_modules.timezone import now_naive as moscow_now
from modules.logs import brain_logger as logger
from sqlalchemy import select


async def get_next_month_start() -> datetime:
    """
    Получить дату начала следующего месяца.
    """
    now = moscow_now()
    if now.month == 12:
        return datetime(now.year + 1, 1, 1, 0, 0, 0)
    else:
        return datetime(now.year, now.month + 1, 1, 0, 0, 0)


async def get_next_year_start() -> datetime:
    """
    Получить дату начала следующего года.
    """
    now = moscow_now()
    return datetime(now.year + 1, 1, 1, 0, 0, 0)


async def check_and_create_monthly_reset_task():
    """
    Проверить наличие задачи сброса месячной статистики.
    Если задачи нет, создать её.
    """
    try:
        # Ищем существующую задачу сброса
        existing_tasks = await ScheduledTask.filter_by(
            function_path="modules.notifications.reset_monthly_tasks"
        )
        
        if existing_tasks:
            logger.info(f"Задача сброса месячной статистики уже существует: {existing_tasks[0].task_id}")
            return
        
        # Создаём новую задачу
        next_month = await get_next_month_start()
        
        task = await ScheduledTask.create(
            task_id=uuid4(),
            card_id=None,
            function_path="modules.notifications.reset_monthly_tasks",
            arguments={},
            execute_at=next_month
        )
        
        logger.info(f"Создана задача сброса месячной статистики на {next_month}: {task.task_id}")
        
    except Exception as e:
        logger.error(f"Ошибка создания задачи сброса месячной статистики: {e}", exc_info=True)


async def check_and_create_yearly_reset_task():
    """
    Проверить наличие задачи сброса годовой статистики.
    Если задачи нет, создать её.
    """
    try:
        # Ищем существующую задачу сброса
        existing_tasks = await ScheduledTask.filter_by(
            function_path="modules.notifications.reset_yearly_tasks"
        )
        
        if existing_tasks:
            logger.info(f"Задача сброса годовой статистики уже существует: {existing_tasks[0].task_id}")
            return
        
        # Создаём новую задачу
        next_year = await get_next_year_start()
        
        task = await ScheduledTask.create(
            task_id=uuid4(),
            card_id=None,
            function_path="modules.notifications.reset_yearly_tasks",
            arguments={},
            execute_at=next_year
        )
        
        logger.info(f"Создана задача сброса годовой статистики на {next_year}: {task.task_id}")
        
    except Exception as e:
        logger.error(f"Ошибка создания задачи сброса годовой статистики: {e}", exc_info=True)


async def init_reset_tasks():
    """
    Инициализация задач сброса при старте API.
    Проверяет и создаёт задачи сброса месячной и годовой статистики.
    """
    logger.info("Проверка задач сброса статистики...")
    
    await check_and_create_monthly_reset_task()
    await check_and_create_yearly_reset_task()
    
    logger.info("Проверка задач сброса завершена")
