from modules.exec.executor import BaseExecutor
from modules.logs import logger
from modules.constants import EXECUTORS
from modules.json_format import check_env_config
from modules.function_way import str_to_func
from typing import Dict, List, Type
import asyncio
import traceback

class ExecutorManager:
    """Менеджер исполнителей"""

    def __init__(self):
        self.executors: Dict[str, BaseExecutor] = {}

    def register(self, executor: BaseExecutor):
        """Зарегистрировать исполнителя"""
        logger.info(
            f"{executor.get_name()} ({executor.get_type()}) is available: {executor.is_available()}"
            )
        if executor.is_available():
            self.executors[executor.get_name()] = executor

    def get(self, executor_name: str) -> Type[BaseExecutor]:
        """Получить исполнителя"""
        return self.executors.get(executor_name)

    def get_available(self) -> List[str]:
        """Получить список доступных исполнителей"""
        return list(self.executors.keys())

    def start_all(self):
        """Запустить всех исполнителей"""
        tasks = []
        for executor in self.executors.values():
            executor.is_running = True
            tasks.append(
                asyncio.create_task(executor.start_polling()
                ))

        return tasks

manager = ExecutorManager()


async def executors_start():
    logger.info("Starting Executors...")

    for exe_name, executor_data in EXECUTORS.items():
        base_class = str_to_func(executor_data['base_class'])

        try:
            executor = base_class(
                config=check_env_config(
                    executor_data['config'] # Заменяем данные на переменные из окружения
                    ),
                executor_name=exe_name
            )
        except Exception as e:
            logger.error(
                f"Error initializing {exe_name} executor: {e}\n{traceback.format_exc()}"
            )
            continue
        manager.register(executor)

    logger.info(
        f"Registered executors: {list(manager.executors.keys())}"
        )
    tasks = manager.start_all()
    return tasks