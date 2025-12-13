
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

from database.core import create_superuser, create_tables
from global_modules.middlewares.logs_mid import RequestLoggingMiddleware

from routers.standart import router as standart_router
from routers.card import router as card_router
from routers.ai import router as ai_router
from routers.kaiten import router as kaiten_router
from routers.kaiten_files import router as kaiten_files_router
from routers.user import router as user_router
from routers.scene import router as scene_router

from global_modules.api_configurate import get_fastapi_app

from modules.logs import brain_logger
from modules.config_kaiten import sync_kaiten_settings
from modules.scheduler import TaskScheduler
from modules.reset_tasks import init_reset_tasks
from database.connection import session_factory
import asyncio
from modules.api_client import executors_api

# Глобальный экземпляр планировщика
scheduler = None


async def create_sheduler():
    global scheduler

    executors_status = 0
    while not executors_status:
        brain_logger.info("Ожидание запуска executors-api...")
        await asyncio.sleep(3)

        executors_status = await executors_api.available()

    # Запуск планировщика задач
    scheduler = TaskScheduler(
        session_factory=session_factory, check_interval=10
        )
    await scheduler.start()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler

    # Startup
    # Инициализация кеша
    FastAPICache.init(InMemoryBackend())
    
    brain_logger.info("Апи запускается...")
    await create_tables()
    brain_logger.info(
        "Таблицы в базе данных созданы или уже существуют.")
    await create_superuser()

    await sync_kaiten_settings()

    # Проверка и создание задач сброса статистики
    await init_reset_tasks()

    # Запуск планировщика задач
    scheduler_task = asyncio.create_task(create_sheduler())

    yield

    # Shutdown
    brain_logger.info("Stopping task scheduler...")
    if scheduler:
        await scheduler.stop()
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass

app = get_fastapi_app(
    title="API",
    version="1.0.0",
    description="Brain API",
    debug=False,
    lifespan=lifespan,
    limiter=True,
    middlewares=[],
    routers=[
        standart_router, card_router, ai_router,
        kaiten_router, kaiten_files_router, user_router,
        scene_router
    ],
    api_logger=brain_logger
)
app.add_middleware(RequestLoggingMiddleware, logger=brain_logger)