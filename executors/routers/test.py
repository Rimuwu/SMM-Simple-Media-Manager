from fastapi import APIRouter, Request
from vk.main import VKExecutor
from modules.executors_manager import manager
from global_modules.limiter import limiter

router = APIRouter(prefix="/test", tags=["test"])

@router.post("/send-message/{executor_name}/{chat_id}")
@limiter.limit("5/minute")
async def test(request: Request, executor_name: str, chat_id: int):
    executor = manager.get(executor_name)

    if not executor:
        return {"error": "Telegram executor not found"}

    await executor.send_message(
        chat_id, "Test message from send-message")

    return {"message": f"sended to {chat_id}"}

@router.get("/create-post")
@limiter.limit("5/minute")
async def create_post(request: Request):
    executor: VKExecutor = manager.get('vk_executor')

    if not executor:
        return {"error": "Executor not found"}

    text = "Создание поста через endpoint /create-post"
    attachments =  []

    result = await executor.create_wall_post(text, attachments)

    return result