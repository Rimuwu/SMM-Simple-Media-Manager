from abc import ABC, abstractmethod
from typing import Dict, Any, List
import asyncio
import logging


class BaseExecutor(ABC):
    """Базовый класс исполнителя"""
    
    def __init__(self, config: dict):
        self.config = config
        self.is_running = False
    
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


ioloop = asyncio.get_event_loop()

class ExecutorManager:
    """Менеджер исполнителей"""
    
    def __init__(self):
        self.executors: Dict[str, BaseExecutor] = {}
    
    def register(self, executor: BaseExecutor):
        """Зарегистрировать исполнителя"""
        if executor.is_available():
            self.executors[executor.get_type()] = executor
    
    def get(self, executor_type: str) -> BaseExecutor:
        """Получить исполнителя"""
        return self.executors.get(executor_type)

    def get_available(self) -> List[str]:
        """Получить список доступных типов"""
        return list(self.executors.keys())

    def start_all(self):
        """Запустить всех исполнителей"""
        tasks = []
        for executor in self.executors.values():
            executor.is_running = True
            tasks.append(
                ioloop.create_task(executor.start_polling()
                ))

        ioloop.run_until_complete(asyncio.gather(*tasks))
        ioloop.close()