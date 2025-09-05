"""
Простой пример использования системы исполнителей
"""
import asyncio
from executor import create_manager, send_message_to_platform
from os import getenv

async def main():
    """Пример использования"""
    
    # Конфигурация
    config = {
        "telegram": {
            "token": getenv("TG_BOT_TOKEN")
        },
        # "vk": {
        #     "token": "YOUR_VK_TOKEN",
        #     "group_id": "YOUR_GROUP_ID"
        # }
    }
    
    # Создаем менеджер
    manager = create_manager(config)

    print(f"Доступные платформы: {manager.get_available()}")
    
    # Отправляем сообщения
    result_tg = await send_message_to_platform(
        manager, "telegram", "1191252229", "Привет из TG!"
    )
    print(f"Telegram: {result_tg}")
    
    result_vk = await send_message_to_platform(
        manager, "vk", "789012", "Привет из VK!"
    )
    print(f"VK: {result_vk}")
    
    # Запускаем пуллинг
    await manager.start_all()


if __name__ == "__main__":
    asyncio.run(main())
