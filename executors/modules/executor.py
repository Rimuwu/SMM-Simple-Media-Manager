from abc import ABC, abstractmethod
from typing import Dict, List, Type
import asyncio

class BaseExecutor(ABC):
    """Базовый класс исполнителя"""

    def __init__(self, config: dict, executor_name: str = "base"):
        self.config = config
        self.is_running = False
        self.executor_name = executor_name

    @abstractmethod
    async def send_message(self, chat_id: str, text: str) -> dict:
        """Отправить сообщение"""
        pass

    @abstractmethod
    async def edit_message(self, chat_id: str, message_id: str, text: str) -> dict:
        """Изменить сообщение"""
        pass

    @abstractmethod
    async def delete_message(self, chat_id: str, message_id: str) -> dict:
        """Удалить сообщение"""
        pass

    @abstractmethod
    async def start_polling(self):
        """Запустить пуллинг"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Проверить доступность исполнителя"""
        pass

    @abstractmethod
    def get_type(self) -> str:
        """Получить тип исполнителя"""
        pass

    def get_name(self) -> str:
        """Получить имя исполнителя"""
        return self.executor_name


class ExecutorManager:
    """Менеджер исполнителей"""

    def __init__(self):
        self.executors: Dict[str, BaseExecutor] = {}

    def register(self, executor: BaseExecutor):
        """Зарегистрировать исполнителя"""
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