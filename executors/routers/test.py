from fastapi import APIRouter, Request
from vk.main import VKExecutor
from modules.executors_manager import manager
from global_modules.limiter import limiter
from pydantic import BaseModel

router = APIRouter(prefix="/test", tags=["test"])

class MessageData(BaseModel):
    executor_name: str
    chat_id: int
    text: str = "Test message from /test/send-message"

@router.post("/send-message")
@limiter.limit("5/minute")
async def test(request: Request, message_data: MessageData):
    executor = manager.get(message_data.executor_name)
    chat_id = message_data.chat_id

    if not executor:
        return {"error": "Telegram executor not found"}

    await executor.send_message(
        chat_id, message_data.text
    )

    return {"message": f"sended to {chat_id}"}

@router.post("/create-post")
@limiter.limit("5/minute")
async def create_post(request: Request):
    executor: VKExecutor = manager.get('vk_executor')

    if not executor:
        return {"error": "Executor not found"}

    text = "Создание поста через endpoint /create-post"
    attachments =  []

    result = await executor.create_wall_post(text, attachments)

    return result