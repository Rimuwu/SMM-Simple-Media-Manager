from global_modules.api_configurate import get_fastapi_app
from modules.logs import executors_logger
from global_modules.middlewares.logs_mid import RequestLoggingMiddleware

from routers.info import router as info_router
from routers.forum import router as forum_router

app = get_fastapi_app(
    title="Executors API",
    version="1.0.0",
    description="Executors API",
    debug=False,
    lifespan=None,
    limiter=True,
    middlewares=[],
    routers=[
        info_router,
        forum_router
        ],
    api_logger=executors_logger,
)
app.add_middleware(RequestLoggingMiddleware, logger=executors_logger)

@app.get("/")
async def root():
    return {"message": f"{app.description} is running! v{app.version}"}