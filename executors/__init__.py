from .executor import ExecutorManager
from .tg.main import TelegramExecutor
from .vk.main import VKExecutor


def create_manager(config: dict) -> ExecutorManager:
    """Создать менеджер с исполнителями"""
    manager = ExecutorManager()
    
    # Telegram
    if "telegram" in config:
        tg = TelegramExecutor(config["telegram"])
        manager.register(tg)
    
    # VK
    if "vk" in config:
        vk = VKExecutor(config["vk"])
        manager.register(vk)
    
    return manager


async def send_message_to_platform(manager: ExecutorManager, platform: str, chat_id: str, text: str) -> dict:
    """Отправить сообщение на платформу"""
    executor = manager.get(platform)
    if not executor:
        return {"success": False, "error": f"Platform {platform} not available"}
    
    return await executor.send_message(chat_id, text)