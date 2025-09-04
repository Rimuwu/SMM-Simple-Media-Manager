from fastapi import APIRouter
from sqlalchemy import text
from database.connection import engine

router = APIRouter(prefix="/db", tags=["db"])

@router.get("/health")
async def db_health():
    """Проверка доступности и версии БД."""

    try:
        async with engine.connect() as conn:  # type: ignore
            result = await conn.execute(text("SELECT 1, version()"))
            row = result.first()
            return {"ok": True, "result": row._asdict() if row else None}
    except Exception as e:
        return {"ok": False, "error": str(e)}