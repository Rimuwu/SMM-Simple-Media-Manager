from fastapi import APIRouter, Request
from sqlalchemy import text
from database.connection import engine
from global_modules.limiter import limiter

router = APIRouter()

@router.get("/db/health")
async def db_health():
    """Проверка доступности и версии БД."""

    try:
        async with engine.connect() as conn:  # type: ignore
            result = await conn.execute(text("SELECT 1, version()"))
            row = result.first()
            return {"ok": True, "result": row._asdict() if row else None}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.get("/")
@limiter.limit("2/second")
async def root(request: Request):
    return {"message": f"{request.app.description} is running! v{request.app.version}"}