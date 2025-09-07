from fastapi import APIRouter
from modules.executors_manager import manager

router = APIRouter(prefix="/test", tags=["test"])

@router.get("/send-message/{executor_name}/{chat_id}")
async def test(executor_name: str, chat_id: int):
    executor = manager.get(executor_name)

    if not executor:
        return {"error": "Telegram executor not found"}

    await executor.send_message(
        chat_id, "Test message from send-message")

    return {"message": f"sended to {chat_id}"}