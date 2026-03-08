"""
Точка входа монолита SMM.
Запускает: БД, планировщик задач, Telegram-бот (polling), VK-исполнитель.
"""
import asyncio

# app/ — корень Python-пакета; при запуске из app/ — sys.path настроен верно.
# При запуске через docker: WORKDIR /app, CMD ["python", "main.py"]


async def main():
    # ──────────────── 1. Инициализация БД ────────────────
    from database.core import create_tables, create_superuser
    await create_tables()
    await create_superuser()

    # ──────────────── 2. Запуск исполнителей (TG, VK) ────
    from modules.exec.executors_manager import manager, executors_start
    from modules.exec import executor_bridge

    await executors_start()
    executor_bridge.set_manager(manager)

    # ──────────────── 3. Планировщик задач ───────────────
    from database.connection import session_factory
    from modules.tasks.scheduler import TaskScheduler

    scheduler = TaskScheduler(session_factory=session_factory)

    # ──────────────── 4. Запуск всего вместе ─────────────
    executor_tasks = manager.start_all()
    scheduler_task = asyncio.create_task(scheduler.start())

    all_tasks = executor_tasks + [scheduler_task]

    await asyncio.gather(*all_tasks, return_exceptions=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановка приложения.")
