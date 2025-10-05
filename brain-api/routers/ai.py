from fastapi import APIRouter
from pydantic import BaseModel
from modules.ai import send


router = APIRouter(prefix="/ai")

# Модель данных для создания карты
class AiRequest(BaseModel):
    prompt: str


@router.post("/send")
async def ai(data: AiRequest):
    response = send(data.prompt)
    return response