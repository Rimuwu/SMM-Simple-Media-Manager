"""
Простой пример использования системы исполнителей
"""
import asyncio
from executor import ExecutorManager
from global_modules.logs import logger
from modules.constants import EXECUTORS
from modules.json_format import check_env_config
from global_modules.function_way import str_to_func

manager = ExecutorManager()

async def main():
    logger.info("Starting Executors...")

    for exe_name, executor_data in EXECUTORS.items():
        base_class = str_to_func(executor_data['base_class'])

        executor = base_class(
            config=check_env_config(
                executor_data['config'] # Заменяем данные на переменные из окружения
                ),
            executor_name=exe_name
        )
        manager.register(executor)

    logger.info(f"Registered executors: {list(manager.executors.keys())}")
    tasks = manager.start_all()
 
    # Отправляем тестовое сообщение
    tg = manager.get("telegram_executor")
    await tg.send_message(
        1191252229, "Test message from main.py")

    # Запускаем все таски
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
