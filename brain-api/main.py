from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

from database.core import create_superuser, create_tables
from global_modules.limiter import limiter
from middlewares.logs_mid import RequestLoggingMiddleware

from routers.db_health import router as db_health_router
from routers.user import router as user_router
from routers.card import router as card_router

from global_modules.api_configurate import get_fastapi_app

from modules.logs import brain_logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    brain_logger.info("API is starting up...")
    brain_logger.info("Creating missing tables on startup...")
    await create_tables()
    await create_superuser()

    yield

    # Shutdown

app = get_fastapi_app(
    title="API",
    version="1.0.0",
    description="Brain API",
    debug=False,
    lifespan=lifespan,
    limiter=True,
    middlewares=[],
    routers=[
        db_health_router, user_router, card_router
    ],
    api_logger=brain_logger
)
app.add_middleware(RequestLoggingMiddleware, logger=brain_logger)

@app.get("/")
@limiter.limit("2/second")
async def root(request: Request):
    return {"message": f"{app.description} is running! v{app.version}"}