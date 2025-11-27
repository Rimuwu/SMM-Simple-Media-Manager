"""
Планировщик задач для выполнения отложенных функций.

Основные возможности:
- Периодическая проверка запланированных задач
- Динамический импорт и выполнение функций
- Автоматическое удаление выполненных задач
- Логирование ошибок выполнения
"""

import asyncio
import importlib
from datetime import datetime
from typing import Callable, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from models.ScheduledTask import ScheduledTask
from models.Card import Card

logger = logging.getLogger(__name__)


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
                ScheduledTask.execute_at <= datetime.utcnow()
            )
            result = await session.execute(query)
            tasks = result.scalars().all()
            
            for task in tasks:
                await self._execute_task(task, session)
    
    async def _execute_task(self, task: ScheduledTask, session: AsyncSession):
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
            
            # Выполняем функцию
            if asyncio.iscoroutinefunction(func):
                await func(**task.arguments)
            else:
                func(**task.arguments)
            
            logger.info(f"Задача {task.task_id} выполнена успешно")
            
        except Exception as e:
            logger.error(f"Ошибка выполнения задачи {task.task_id}: {e}", exc_info=True)
        
        finally:
            # Удаляем задачу после выполнения (независимо от результата)
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
