from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.Card import Card, CardStatus
from services.card_service import CardService

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
    card = await CardService.create_card(
        **card_data.__dict__)
    return card

@router.get("/all")
async def get_all_cards():
    cards = await CardService.get_all_cards()
    return cards

@router.delete("/delete/{card_id}")
async def delete_card(card_id: str):
    success = await CardService.delete_card(card_id)
    if not success:
        raise HTTPException(status_code=404, 
                            detail="Card not found")
    return {"detail": "Card deleted successfully"}

@router.get("/{card_id}")
async def get_card_by_id(card_id: str):
    cards = await CardService.get_all_cards()
    for card in cards:
        if str(card.card_id) == card_id:
            return card
    raise HTTPException(status_code=404, 
                        detail="Card not found")

@router.get("/by_status/{status}")
async def get_cards_by_status(status: CardStatus):
    cards = await CardService.get_by_status(status)
    return cards