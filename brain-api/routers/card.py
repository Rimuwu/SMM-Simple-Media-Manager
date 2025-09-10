from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.Card import Card, CardStatus
from services.user_service import UserService

router = APIRouter(prefix="/card", tags=["card"])

class CardCreate(BaseModel):
    name: str
    description: str | None
    customer_id: int | None
    executor_id: int | None
    clients: list[str]
    need_check: bool
    tags: list[str]
    deadline: datetime | None

@router.post("/create")
async def create_card(card_data: CardCreate):
    pass
    