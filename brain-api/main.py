from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

from database.core import create_tables
from global_modules.limiter import limiter
from middlewares.logs_mid import RequestLoggingMiddleware

from routers.db_health import router as db_health_router
from global_modules.logs import logger
from global_modules.api_configurate import get_fastapi_app

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("API is starting up...")
    logger.info("Creating missing tables on startup...")
    await create_tables()

    yield

    # Shutdown
    logger.info("🛑 API is shutting down...")

app = get_fastapi_app(
    title="API",
    version="1.0.0",
    description="Brain API",
    debug=False,
    lifespan=lifespan,
    limiter=True,
    middlewares=[RequestLoggingMiddleware],
    routers=[db_health_router]
)

@app.get("/")
@limiter.limit("2/second")
async def root(request: Request):
    return {"message": f"{app.description} is running! v{app.version}"}