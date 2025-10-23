from fastapi import APIRouter, Request
from modules.text_generators import forum_message
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
    card_id: str

@router.post("/send-message-to-forum")
async def send_message_to_forum(message: ForumMessage):

    data = await forum_message(message.card_id)

    return {"success": data.get("success", False),
            "message_id": data.get("message_id", None),
            "error": data.get("error", None)}