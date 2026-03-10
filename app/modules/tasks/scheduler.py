import asyncio
import importlib
from datetime import datetime, timedelta
from typing import Callable
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ScheduledTask import ScheduledTask
from app.modules.components.timezone import now_naive as moscow_now
from app.modules.components.logs import logger

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.card.Card import Card


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
            
            # Если указан card_id — убеждаемся, что карточка существует (передаём только card_id)
            if 'card_id' in task.arguments:
                exists = await session.get('Card', task.arguments['card_id'])
                if not exists:
                    logger.error(f"Карточка {task.arguments['card_id']} не найдена")
                    await session.delete(task)
                    await session.commit()
                    return

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
    
    @staticmethod
    async def schedule_task(
        session_factory: AsyncSession,
        function_path: str,
        arguments: dict,
        execute_at: datetime,
        card_id: str = None
    ) -> ScheduledTask:
        """Создать и сохранить запланированную задачу."""

        async with session_factory() as session:
            task = await ScheduledTask.create(
                session=session,
                function_path=function_path,
                arguments=arguments,
                execute_at=execute_at,
                card_id=card_id
            )
            return task