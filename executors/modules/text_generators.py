
from datetime import datetime
from pprint import pprint
from aiogram import Bot, Dispatcher
from tg.main import TelegramExecutor
from modules.executors_manager import manager
from modules.constants import SETTINGS
from modules.api_client import brain_api, get_cards, update_card, get_users
from global_modules.classes.enums import CardStatus
from modules.utils import get_telegram_user

forum_topic = SETTINGS.get('forum_topic', 0)
group_forum = SETTINGS.get('group_forum', 0)

pass_tag = '#НовоеЗадание'
edited_tag = '#ЗаданиеВыполняется'
open_chacked_tag = '#ЗаданиеТребуетПроверки'
chacked_tag = '#ЗаданиеНаПроверке'



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

async def text_getter(card: dict, tag: str, 
                      client_executor: TelegramExecutor) -> str:

    name = card.get("name", "No Title")
    description = card.get("description", "No Description")
    deadline = card.get("deadline", "Без дедлайна")
    tags = card.get("tags", []) if card.get("tags", []) else ["Без тегов"]
    need_check = "✅" if card.get("need_check", False) else "❌"
    
    if deadline != "Без дедлайна":
        try:
            dt = datetime.fromisoformat(deadline)
            deadline = dt.strftime('%d.%m.%Y %H:%M')
        except: pass


    data_list = []
    for i in ['executor_id', 'customer_id']:

        _id = card.get(i)

        if _id is not None:
            users = await get_users(user_id=_id)
            user = users[0] if users else None

            if user is not None:
                tg_user = await get_telegram_user(
                    bot=client_executor.bot,
                    telegram_id=user.get("telegram_id")
                )
                if tg_user:
                    username = f'@{tg_user.username}' if tg_user.username else f'`{tg_user.full_name}`'
            else:
                username = f"ID: {card.get(i)} (ошибка получения)"
        else:
            username = "👤 Не назначен"

        data_list.append(username)

    executor_nick, customer_nick = data_list

    text = (f'Статус: {tag}\n'
        f'Появилось новое задание!'
        f'\n'
        f'\nНазвание: `{name}`'
        f'\nДедлайн: {deadline}'
        f'\nИсполнитель: {executor_nick}'
        f'\nЗаказчик: {customer_nick}'
        f'\nТеги: {", ".join(tags)}'
        f'\nПроверяемый: {need_check}'
        f'\n\n```Описание'
        f'\n{description}'
        f'```'
    )

    return text

async def forum_message(card_id: str, status: str):
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

    if status == CardStatus.pass_.value:
        tag = pass_tag
        markup = [
            {
                "text": "Забрать задание",
                "callback_data": "take_task"
            }
        ]

    elif status == CardStatus.edited.value:

        tag = edited_tag

        markup = [
            {
                "text": "Задание взято",
                "callback_data": " "
            }
        ]

    text = await text_getter(card, tag, client_executor)

    if card.get("forum_message_id", None) is None:

        data = await client_executor.send_message(
            reply_to_message_id=forum_topic,
            chat_id=group_forum,
            text=text,
            list_markup=markup,
            parse_mode="Markdown"
        )

    else:
        data = await client_executor.edit_message(
            chat_id=group_forum,
            message_id=card["forum_message_id"],
            text=text,
            parse_mode="Markdown",
            list_markup=markup
        )

        if not data.get("success", False):
            print(data)

            data = await client_executor.send_message(
                reply_to_message_id=forum_topic,
                chat_id=group_forum,
                text=text,
                list_markup=markup,
                parse_mode="Markdown"
            )

    status = data.get("success", False)
    if not status:
        return {
            "error": f"Не удалось отправить сообщение в форум. Error: {data.get('error', '')}", 
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