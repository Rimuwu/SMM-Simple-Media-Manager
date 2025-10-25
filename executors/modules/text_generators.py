
from aiogram import Bot, Dispatcher
from tg.main import TelegramExecutor
from modules.executors_manager import manager
from modules.constants import SETTINGS
from modules.api_client import brain_api, get_cards, update_card, get_users
from global_modules.classes.enums import CardStatus

forum_topic = SETTINGS.get('forum_topic', 0)
group_forum = SETTINGS.get('group_forum', 0)


async def card_deleted(card_id: str):
    """Обработчик удаления карточки"""
    client_executor: TelegramExecutor = manager.get(
        "telegram_executor"
    )

    if not client_executor:
        return {"error": "Executor not found", "success": False}

    cards = await get_cards(card_id=card_id)
    if not cards:
        return {"error": "Card not found", "success": False}
    else:
        card = cards[0]
        message_id = card.get("forum_message_id", None)
        if not message_id:
            return {"error": "No forum message ID", "success": False}

    data = await client_executor.delete_message(
        chat_id=group_forum,
        message_id=message_id
    )

    status = data.get("success", False)
    if not status:
        return {
            "error": "Не удалось удалить сообщение из форума", 
            "success": False
        }

    return {"success": True}

async def forum_message(card_id: str):
    """Отправить сообщение в форум о новой карточке и обновить карточку с ID сообщения"""

    client_executor: TelegramExecutor = manager.get(
        "telegram_executor"
        )

    if not client_executor:
        return {"error": "Executor not found", "success": False}

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

    data = await client_executor.send_message(
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

async def card_executed(card_id: str, telegram_id: int):
    """Отправить сообщение в форум о новой карточке и обновить карточку с ID сообщения"""

    client_executor: TelegramExecutor = manager.get(
        "telegram_executor"
    )

    if not client_executor:
        return {"error": "Executor not found", "success": False}

    users = await get_users(telegram_id=telegram_id)
    cards = await get_cards(card_id=card_id)
    if not cards:
        return {"error": "Card not found", "success": False}
    elif not users:
        return {"error": "User not found", "success": False}
    else:
        card = cards[0]
        executor_id = users[0]['user_id']
        markup = [
            {
                "text": "Задание взято",
                "callback_data": " "
            }
        ]

        await client_executor.update_markup(
            chat_id=group_forum,
            message_id=card['forum_message_id'],
            list_markup=markup
        )

        await update_card(
            card_id=card_id,
            executor_id=executor_id,
            status=CardStatus.edited
        )

        await client_executor.send_message(
            chat_id=executor_id,
            text=f'Вы взяли задание: {card["name"]}',
        )

    return {"success": True}