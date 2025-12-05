
from datetime import datetime
from pprint import pprint
from aiogram import Bot, Dispatcher
from tg.main import TelegramExecutor
from modules.executors_manager import manager
from modules.constants import SETTINGS, CLIENTS
from modules.api_client import brain_api, get_cards, update_card, get_users
from modules.post_generator import generate_post
from global_modules.classes.enums import CardStatus
from modules.utils import get_telegram_user

forum_topic = SETTINGS.get('forum_topic', 0)
group_forum = SETTINGS.get('group_forum', 0)
complete_topic = SETTINGS.get('complete_topic', 0)


pass_tag = '#НовоеЗадание'
edited_tag = '#ЗаданиеВыполняется'
checked_tag = '#ЗаданиеНаПроверке'
done_tag = '#ЗаданиеВыполнено'


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
    description = card.get("description") or "No Description"
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

    tag = pass_tag
    if status == CardStatus.pass_.value:
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
    
    elif status == CardStatus.review.value:
        tag = checked_tag

        markup = [
            {
                "text": "Задание на проверке",
                "callback_data": " "
            }
        ]

    elif status == CardStatus.ready.value:
        tag = done_tag

        markup = [
            {
                "text": "Задание выполнено",
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


async def download_kaiten_files(task_id: int, file_names: list[str]) -> list[bytes]:
    """
    Скачать файлы из Kaiten по именам.
    """
    if not task_id or not file_names:
        return []
    
    downloaded_files = []
    
    try:
        response, status = await brain_api.get(f"/kaiten/get-files/{task_id}")
        
        if status != 200 or not response.get('files'):
            return []
        
        kaiten_files = response['files']
        
        for file_name in file_names:
            target_file = next(
                (f for f in kaiten_files if f.get('name') == file_name),
                None
            )
            
            if not target_file:
                continue
            
            file_id = target_file.get('id')
            if not file_id:
                continue
            
            file_data, dl_status = await brain_api.get(
                f"/kaiten/files/{file_id}",
                params={"task_id": task_id},
                return_bytes=True
            )
            
            if dl_status == 200 and isinstance(file_data, bytes):
                downloaded_files.append(file_data)
    
    except Exception as e:
        print(f"Error downloading files from Kaiten: {e}")
    
    return downloaded_files


async def send_complete_preview(card_id: str, client_key: str) -> dict:
    """
    Отправить превью поста в complete_topic.
    Отправляет сообщение с картинками и отформатированным текстом поста,
    затем отправляет название задачи и имя клиента.
    
    Args:
        card_id: ID карточки
        client_key: Ключ клиента для которого создаётся превью
        
    Returns:
        dict с success и message_id (или error)
    """
    client_executor: TelegramExecutor = manager.get("telegram_executor")
    
    if not client_executor:
        return {"error": "Executor not found", "success": False}
    
    cards = await get_cards(card_id=card_id)
    if not cards:
        return {"error": "Card not found", "success": False}
    
    card = cards[0]
    
    # Получаем конфигурацию клиента
    client_config = CLIENTS.get(client_key)
    if not client_config:
        return {"error": f"Client {client_key} not found", "success": False}
    
    client_label = client_config.get('label', client_key)
    
    # Генерируем текст поста
    content = card.get("content") or card.get("description") or ""
    tags = card.get("tags", [])
    
    # Определяем платформу по ключу клиента
    platform = "vk" if "vk" in client_key.lower() else "telegram"
    
    post_text = generate_post(
        content=content,
        tags=tags,
        platform=platform,
        client_key=client_key
    )
    
    # Загружаем изображения если есть
    task_id = card.get("task_id")
    post_images = card.get("post_images", []) or []
    
    downloaded_images = []
    if task_id and post_images:
        downloaded_images = await download_kaiten_files(task_id, post_images)
    
    message_id = None
    
    try:
        # Отправляем пост с изображениями или без
        if downloaded_images:
            if len(downloaded_images) == 1:
                result = await client_executor.send_photo(
                    chat_id=group_forum,
                    photo=downloaded_images[0],
                    caption=post_text,
                    parse_mode="HTML"
                )
                if result.get("success"):
                    message_id = result.get("message_id")
            else:
                result = await client_executor.send_media_group(
                    chat_id=group_forum,
                    media=downloaded_images,
                    caption=post_text,
                    parse_mode="HTML"
                )
                if result.get("success"):
                    message_id = result.get("message_id")
        else:
            result = await client_executor.send_message(
                chat_id=group_forum,
                text=post_text,
                reply_to_message_id=complete_topic,
                parse_mode="HTML"
            )
            if result.get("success"):
                message_id = result.get("message_id")
        
        if not message_id:
            return {"error": f"Failed to send preview: {result.get('error', 'Unknown error')}", "success": False}
        
        # Отправляем информацию о задаче и клиенте
        card_name = card.get("name", "Без названия")
        info_text = f"📝 <b>{card_name}</b>\n📢 Канал: <b>{client_label}</b>"
        
        await client_executor.send_message(
            chat_id=group_forum,
            text=info_text,
            reply_to_message_id=complete_topic,
            parse_mode="HTML"
        )
        
        return {"success": True, "message_id": message_id}
    
    except Exception as e:
        return {"error": str(e), "success": False}


async def update_complete_preview(card_id: str, client_key: str, message_id: int) -> dict:
    """
    Обновить превью поста в complete_topic.
    
    Args:
        card_id: ID карточки
        client_key: Ключ клиента
        message_id: ID сообщения для обновления
        
    Returns:
        dict с success (или error)
    """
    client_executor: TelegramExecutor = manager.get("telegram_executor")
    
    if not client_executor:
        return {"error": "Executor not found", "success": False}
    
    cards = await get_cards(card_id=card_id)
    if not cards:
        return {"error": "Card not found", "success": False}
    
    card = cards[0]
    
    # Получаем конфигурацию клиента
    client_config = CLIENTS.get(client_key)
    if not client_config:
        return {"error": f"Client {client_key} not found", "success": False}
    
    # Генерируем текст поста
    content = card.get("content") or card.get("description") or ""
    tags = card.get("tags", [])
    
    platform = "vk" if "vk" in client_key.lower() else "telegram"
    
    post_text = generate_post(
        content=content,
        tags=tags,
        platform=platform,
        client_key=client_key
    )
    
    try:
        # Пытаемся обновить сообщение
        # Примечание: media group нельзя редактировать, только текст/caption
        result = await client_executor.edit_message(
            chat_id=group_forum,
            message_id=str(message_id),
            text=post_text,
            parse_mode="HTML"
        )
        
        if result.get("success"):
            return {"success": True}
        else:
            # Если редактирование не удалось (например, это media group),
            # удаляем старое и отправляем новое
            await client_executor.delete_message(
                chat_id=group_forum,
                message_id=str(message_id)
            )
            
            return await send_complete_preview(card_id, client_key)
    
    except Exception as e:
        return {"error": str(e), "success": False}


async def delete_complete_preview(message_id: int) -> dict:
    """
    Удалить превью поста из complete_topic.
    
    Args:
        message_id: ID сообщения для удаления
        
    Returns:
        dict с success (или error)
    """
    client_executor: TelegramExecutor = manager.get("telegram_executor")
    
    if not client_executor:
        return {"error": "Executor not found", "success": False}
    
    try:
        result = await client_executor.delete_message(
            chat_id=group_forum,
            message_id=str(message_id)
        )
        
        return {"success": result.get("success", False)}
    
    except Exception as e:
        return {"error": str(e), "success": False}