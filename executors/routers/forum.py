from fastapi import APIRouter, Request
from modules.text_generators import forum_message, card_deleted, send_complete_preview, update_complete_preview, delete_complete_preview
from tg.main import TelegramExecutor
from modules.executors_manager import manager
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional
from modules.constants import SETTINGS
from modules.api_client import brain_api
from global_modules.classes.enums import CardStatus

router = APIRouter(prefix="/forum")

forum_topic = SETTINGS.get('forum_topic', 0)
group_forum = SETTINGS.get('group_forum', 0)
complete_topic = SETTINGS.get('complete_topic', 0)

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

@router.delete("/delete-forum-message-for-id/{message_id}")
async def delete_forum_message_for_id(message_id: str):
    
    client_executor: TelegramExecutor = manager.get(
        "telegram_executor"
    )

    data = await client_executor.delete_message(
        chat_id=group_forum,
        message_id=message_id
    )

    return {"success": data.get("success", False),
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


# ==================== Complete Topic (Превью готовых постов) ====================

class CompletePreviewRequest(BaseModel):
    card_id: str
    client_key: str

@router.post("/send-complete-preview")
async def send_complete_preview_endpoint(request: CompletePreviewRequest):
    """
    Отправить превью готового поста в complete_topic.
    Отправляет сообщение с картинками и отформатированным текстом,
    затем информацию о задаче, клиенте и дате отправки.
    """
    data = await send_complete_preview(request.card_id, request.client_key)
    
    return {
        "success": data.get("success", False),
        "post_id": data.get("post_id", None),
        "post_ids": data.get("post_ids", []),  # Список всех ID для медиа-групп
        "info_id": data.get("info_id", None),
        "error": data.get("error", None)
    }


class UpdateCompletePreviewRequest(BaseModel):
    card_id: str
    client_key: str
    post_id: int
    info_id: Optional[int] = None
    post_ids: Optional[list[int]] = None  # Список всех ID для медиа-групп

@router.post("/update-complete-preview")
async def update_complete_preview_endpoint(request: UpdateCompletePreviewRequest):
    """
    Обновить превью готового поста в complete_topic.
    """
    data = await update_complete_preview(
        request.card_id,
        request.client_key,
        request.post_id,
        request.info_id,
        request.post_ids
    )
    
    return {
        "success": data.get("success", False),
        "post_id": data.get("post_id", None),
        "post_ids": data.get("post_ids", []),  # Список всех ID для медиа-групп
        "info_id": data.get("info_id", None),
        "error": data.get("error", None)
    }


class DeleteCompletePreviewRequest(BaseModel):
    post_id: Optional[int] = None  # Старый формат
    info_id: Optional[int] = None
    post_ids: Optional[list[int]] = None  # Новый формат - список ID

@router.post("/delete-complete-preview")
async def delete_complete_preview_endpoint(request: DeleteCompletePreviewRequest):
    """
    Удалить превью готового поста из complete_topic.
    Удаляет все сообщения: с постом (включая медиа-группы) и с информацией.
    """
    data = await delete_complete_preview(
        post_id=request.post_id, 
        info_id=request.info_id,
        post_ids=request.post_ids
    )
    
    return {
        "success": data.get("success", False),
        "error": data.get("error", None)
    }