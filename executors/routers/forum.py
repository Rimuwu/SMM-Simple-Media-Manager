from fastapi import APIRouter, Request
from tg.main import TelegramExecutor
from modules.executors_manager import manager
from fastapi import APIRouter, Request
from pydantic import BaseModel
from modules.constants import SETTINGS
from modules.api_client import brain_api

router = APIRouter(prefix="/forum")

forum_topic = SETTINGS.get('forum_topic', 0)
group_forum = SETTINGS.get('group_forum', 0)

class ForumMessage(BaseModel):
    title: str
    deadline: str
    description: str = ""

@router.post("/send-message-to-forum")
async def send_message_to_forum(message: ForumMessage):
    executor: TelegramExecutor = manager.get('telegram_executor')
    if not executor:
        return {"error": "Telegram executor not found"}

    data = await executor.send_message(
        reply_to_message_id=forum_topic,
        chat_id=group_forum,
        text=message.title + "\n" + message.deadline + "\n" + message.description
    )
    status = data.get("success", False)
    if not status:
        return {"error": data.get("error", "Unknown error"), 
                "success": False}

    message_id = data.get("message_id", None)
    return {"success": True, "message_id": message_id}