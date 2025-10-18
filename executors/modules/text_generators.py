
from tg.main import TelegramExecutor
from modules.executors_manager import manager
from modules.constants import SETTINGS
from modules.api_client import brain_api, get_cards

forum_topic = SETTINGS.get('forum_topic', 0)
group_forum = SETTINGS.get('group_forum', 0)

executor: TelegramExecutor = manager.get(
    'telegram_executor') # type: ignore

async def forum_message(card_id: str):
    """Отправить сообщение в форум о новой карточке и обновить карточку с ID сообщения"""
    
    cards = await get_cards(card_id=card_id)
    if not cards:
        return {"error": "Card not found", "success": False}
    else:
        card = cards[0]
        name = card.get("name", "No Title")
        description = card.get("description", "No Description")
        deadline = card.get("deadline", "No Deadline")
        tags = card.get("tags", [])

    markup = [
        {
            "text": "Забрать задание",
            "callback_data": "take_task"
        }
    ]

    text = f'Появилось новое задание: {name}\n\nОписание: {description}\n\nСрок: {deadline}\n\nТеги: #{", #".join(tags)}'

    data = await executor.send_message(
        reply_to_message_id=forum_topic,
        chat_id=group_forum,
        text=text,
        list_markup=markup
    )

    status = data.get("success", False)
    if not status:
        return {
            "error": "Не удалось отправить сообщение в форум", 
            "success": False
        }

    message_id = data.get("message_id", None)
    return {"success": True, "message_id": message_id}