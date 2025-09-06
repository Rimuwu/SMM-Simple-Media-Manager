from global_modules.api_configurate import get_fastapi_app
from routers.test import router as test_router

app = get_fastapi_app(
    title="Executors API",
    version="1.0.0",
    description="Executors API",
    debug=False,
    lifespan=None,
    limiter=False,
    middlewares=[],
    routers=[test_router]
)

@app.get("/")
async def root():
    return {"message": f"{app.description} is running! v{app.version}"}