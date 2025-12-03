from fastapi import APIRouter, Request
from modules.text_generators import forum_message, card_deleted
from tg.main import TelegramExecutor
from modules.executors_manager import manager
from fastapi import APIRouter, Request
from pydantic import BaseModel
from modules.constants import SETTINGS
from modules.api_client import brain_api
from global_modules.classes.enums import CardStatus

router = APIRouter(prefix="/forum")

forum_topic = SETTINGS.get('forum_topic', 0)
group_forum = SETTINGS.get('group_forum', 0)

class ForumMessage(BaseModel):
    card_id: str

@router.post("/send-message-to-forum")
async def send_message_to_forum(message: ForumMessage):

    data = await forum_message(message.card_id, 
                               CardStatus.pass_.value)

    return {"success": data.get("success", False),
            "message_id": data.get("message_id", None),
            "error": data.get("error", None)}

@router.delete("/delete-forum-message/{card_id}")
async def delete_forum_message(card_id: str):

    data = await card_deleted(card_id)

    return {"success": data.get("success", False),
            "message_id": data.get("message_id", None),
            "error": data.get("error", None)}

class UpdateForumMessage(BaseModel):
    card_id: str
    status: str

@router.post("/update-forum-message")
async def update_forum_message(message: UpdateForumMessage):
    """Обновить сообщение на форуме"""
    
    data = await forum_message(
        message.card_id, 
        message.status
    )

    return {
        "success": data.get("success", False),
        "message_id": data.get("message_id", None),
        "error": data.get("error", None)
    }