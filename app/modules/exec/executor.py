from abc import ABC, abstractmethod

class BaseExecutor(ABC):
    """Базовый класс исполнителя"""

    def __init__(self, config: dict, executor_name: str = "base"):
        self.config = config
        self.is_running = False
        self.executor_name = executor_name

    @abstractmethod
    async def send_message(self, chat_id: str, text: str, **kwargs) -> dict:
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