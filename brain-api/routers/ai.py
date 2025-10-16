from fastapi import APIRouter, Request
from pydantic import BaseModel
from modules.ai import send
from global_modules.limiter import limiter

router = APIRouter(prefix="/ai")

# Модель данных для создания карты
class AiRequest(BaseModel):
    prompt: str

@router.post("/send")
@limiter.limit("5/minute")
async def ai(request: Request, data: AiRequest):
    response = send(data.prompt)
    return response