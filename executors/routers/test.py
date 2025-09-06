from fastapi import APIRouter
from modules.executors_manager import manager

router = APIRouter(prefix="/test", tags=["test"])

@router.get("/send-message/{chat_id}")
async def test(chat_id: int):
    tg = manager.get("telegram_executor")
    if not tg:
        return {"error": "Telegram executor not found"}

    await tg.send_message(
        chat_id, "Test message from send-message")

    return {"message": f"sended to {chat_id}"}