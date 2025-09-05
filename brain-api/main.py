from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

from config import settings
from database.core import create_tables
from security.limiter import setup_rate_limiter, limiter
from middlewares.logs_mid import RequestLoggingMiddleware

from routers.db_health import router as db_health_router
from modules.logs import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("API is starting up...")
    logger.info("Creating missing tables on startup...")
    await create_tables()

    yield

    # Shutdown
    logger.info("🛑 API is shutting down...")

# Инициализация FastAPI приложения
app = FastAPI(
    title=getattr(settings, "api_title", "API"),
    version=getattr(settings, "api_version", "1.0.0"),
    description="Brain API",
    debug=False,
    lifespan=lifespan
)

setup_rate_limiter(app)
app.state.logger = logger

# Middleware для логирования запросов
app.add_middleware(RequestLoggingMiddleware)

# Подключение роутеров
app.include_router(db_health_router)

@app.get("/")
@limiter.limit("2/second")
async def root(request: Request):
    return {"message": f"{app.description} is running! v{app.version}"}