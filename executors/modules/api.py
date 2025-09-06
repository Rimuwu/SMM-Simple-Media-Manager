from global_modules.api_configurate import get_fastapi_app
from routers.test import router as test_router
from modules.logs import executors_logger
from middlewares.logs_mid import RequestLoggingMiddleware

app = get_fastapi_app(
    title="Executors API",
    version="1.0.0",
    description="Executors API",
    debug=False,
    lifespan=None,
    limiter=False,
    middlewares=[],
    routers=[test_router],
    api_logger=executors_logger,
)
app.add_middleware(RequestLoggingMiddleware, logger=executors_logger)

@app.get("/")
async def root():
    return {"message": f"{app.description} is running! v{app.version}"}