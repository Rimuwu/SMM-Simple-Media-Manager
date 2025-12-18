from global_modules.api_configurate import get_fastapi_app
from routers.calendar import router as calendar_router
from modules.logs import calendar_logger
from global_modules.middlewares.logs_mid import RequestLoggingMiddleware

app = get_fastapi_app(
    title="Calendar API",
    version="1.0.0",
    description="Calendar API for Google Calendar integration",
    debug=False,
    lifespan=None,
    limiter=False,
    middlewares=[],
    routers=[calendar_router]
)
app.add_middleware(RequestLoggingMiddleware, logger=calendar_logger)

@app.get("/")
async def root():
    return {"message": f"{app.description} is running! v{app.version}"}