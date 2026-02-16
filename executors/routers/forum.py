from fastapi import APIRouter
from modules.text_generators import forum_message, card_deleted, send_complete_preview, update_complete_preview, delete_complete_preview
from tg.main import TelegramExecutor
from modules.executors_manager import manager
from pydantic import BaseModel
from typing import Optional
from modules.constants import SETTINGS, CLIENTS
from global_modules.json_get import open_settings

router = APIRouter(prefix="/forum")

forum_topic = SETTINGS.get('forum_topic', 0)
group_forum = SETTINGS.get('group_forum', 0)
complete_topic = SETTINGS.get('complete_topic', 0)
community_forum = SETTINGS.get('community_forum', 0)

class ForumMessage(BaseModel):
    card_id: str

@router.post("/send-message-to-forum")
async def send_message_to_forum(message: ForumMessage):

    data = await forum_message(message.card_id)

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

@router.post("/update-forum-message")
async def update_forum_message(message: UpdateForumMessage):
    """Обновить сообщение на форуме"""
    
    data = await forum_message(
        message.card_id
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
        "post_ids": data.get("post_ids", None),
        "entities": data.get("entities", []),  # Список всех ID для медиа-групп
        "info_id": data.get("info_id", None),
        "error": data.get("error", None)
    }


class UpdateCompletePreviewRequest(BaseModel):
    card_id: str
    client_key: str
    info_id: Optional[int] = None
    post_ids: Optional[list[int]] = None
    entities: Optional[list[int]] = None

@router.post("/update-complete-preview")
async def update_complete_preview_endpoint(request: UpdateCompletePreviewRequest):
    """
    Обновить превью готового поста в complete_topic.
    """
    data = await update_complete_preview(
        request.card_id,
        request.client_key,
        post_ids=request.post_ids,
        info_id=request.info_id,
        entities=request.entities
    )
    
    return {
        "success": data.get("success", False),
        "post_ids": data.get("post_ids", []),
        "entities": data.get("entities", []),
        "info_id": data.get("info_id", None),
        "error": data.get("error", None)
    }


class DeleteCompletePreviewRequest(BaseModel):
    info_ids: Optional[list[int]] = None
    post_ids: Optional[list[int]] = None
    entities: Optional[list[int]] = None

@router.post("/delete-complete-preview")
async def delete_complete_preview_endpoint(request: DeleteCompletePreviewRequest):
    """
    Удалить превью готового поста из complete_topic.
    Удаляет все сообщения: с постом (включая медиа-группы) и с информацией.
    """
    
    print("Запрос на удаление complete preview:",
        f"post_ids={request.post_ids}, info_ids={request.info_ids}, entities={request.entities}"
    )

    data = await delete_complete_preview(
        info_ids=request.info_ids,
        post_ids=request.post_ids,
        entities=request.entities
    )

    return {
        "success": data.get("success", False),
        "error": data.get("error", None)
    }


class ForwardFirstByTagsRequest(BaseModel):
    source_chat_id: str | int
    message_id: int
    tags: Optional[list[str]] = None
    source_client_key: Optional[str] = None

@router.post("/forward-first-by-tags")
async def forward_first_by_tags(
    request: ForwardFirstByTagsRequest):
    
    print(request)

    client_executor: TelegramExecutor = manager.get("telegram_executor")
    if not client_executor:
        return {"success": False, "error": "Executor not found"}

    settings = open_settings() or {}
    tags_values = settings.get('properties', {}).get('tags', {}).get('values', {})

    client_id = CLIENTS.get(request.source_client_key, {}).get('client_id')

    results: list[dict] = []
    tags_to_process = list(dict.fromkeys(request.tags or []))
    
    print(client_id, tags_to_process)

    for tag in tags_to_process:
        tag_info = tags_values.get(tag, {})
        forward_to_topic = tag_info.get('forward_to_topic')
        if not forward_to_topic:
            results.append({"tag": tag, "skipped": True})
            continue

        print(community_forum, client_id, request.message_id, forward_to_topic)

        try:
            copied = await client_executor.bot.forward_message(
                chat_id=community_forum,
                from_chat_id=client_id,
                message_id=request.message_id,
                message_thread_id=int(forward_to_topic)
            )
            results.append({"tag": tag, "forwarded_message_id": getattr(copied, 'message_id', None)})
        except Exception as e:
            results.append({"tag": tag, "error": str(e)})

    return {"success": True, "results": results}