
from datetime import datetime
from pprint import pprint
from global_modules import brain_client
from tg.main import TelegramExecutor
from modules.executors_manager import manager
from modules.constants import SETTINGS, CLIENTS
from modules.api_client import brain_api, get_cards, update_card, get_users
from modules.post_generator import generate_post
from global_modules.classes.enums import CardStatus
from modules.utils import get_telegram_user
from modules.entities_sender import send_poll_preview, get_entities_for_client
from global_modules.brain_client import brain_client

forum_topic = SETTINGS.get('forum_topic', 0)
group_forum = SETTINGS.get('group_forum', 0)
complete_topic = SETTINGS.get('complete_topic', 0)


pass_tag = '#НовоеЗадание'
edited_tag = '#ЗаданиеВыполняется'
needcheck_tag = '#ЗаданиеНаПроверку'
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
        return {"error": f"Card not found for {card_id}", "success": False}
    else:
        forum_messages = await brain_client.get_messages(
            card_id=card_id, message_type="forum"
        )

        first_or_none = forum_messages[0] if forum_messages else {}

        message_id = first_or_none.get("message_id", None)
        if not message_id:
            return {"error": "No forum message ID", "success": False}

    data = await client_executor.delete_message(
        chat_id=group_forum,
        message_id=message_id
    )

    status = data.get("success", False)
    if not status:
        error_msg = data.get("error", "Unknown error")
        return {
            "error": f"Не удалось удалить сообщение из форума: {error_msg}", 
            "success": False
        }

    return {"success": True}

async def text_getter(card: dict, tag: str, 
                      client_executor: TelegramExecutor) -> str:

    name = card.get("name", "Без названия")
    description = card.get("description") or "Без описания"
    deadline = card.get("deadline", "Без дедлайна")
    tags = card.get("tags", []) if card.get("tags", []
                                            ) else ["Без тегов"]
    need_check = "✅" if card.get("need_check", False) else "❌"
    
    if deadline != "Без дедлайна":
        try:
            dt = datetime.fromisoformat(deadline)
            deadline = dt.strftime('%d.%m.%Y %H:%M')
        except: pass

    data_list = []
    for i in ['executor_id', 'customer_id', 'editor_id']:

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
                    username = f"ID: {card.get(i)}"
            else:
                username = f"ID: {card.get(i)} (ошибка получения)"
        else:
            username = "👤 Не назначен"

        data_list.append(username)

    executor_nick, customer_nick, editor_nick = data_list

    text = (f'Статус: {tag}\n'
        f'Появилось новое задание!'
        f'\n'
        f'\nНазвание: `{name}`'
        f'\nДедлайн: {deadline}'
        f'\nИсполнитель: `{executor_nick}`'
        f'\nЗаказчик: `{customer_nick}`'
        f'\nРедактор: `{editor_nick}`'
        f'\nТеги: {", ".join(tags)}'
        f'\nПроверяемый: {need_check}'
        f'\n\n```Описание'
        f'\n{description[:750]}'
        f'```'
    )

    return text

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

    tag = pass_tag
    markup = []
    
    status = card['status']

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
    
    elif status == CardStatus.review.value and card['editor_id'] is None:
        tag = needcheck_tag

        markup = [
            {
                "text": "Взять на проверку",
                "callback_data": "edit_task"
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

    forum_messages = await brain_client.get_messages(
        card_id=card_id, message_type="forum"
    )
    
    first_or_none = forum_messages[0] if forum_messages else None

    if not first_or_none:

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
            message_id=first_or_none['message_id'],
            text=text,
            parse_mode="Markdown",
            list_markup=markup
        )

        error = data.get("error", "")
        if 'not found' in error.lower():
            
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
            executor_id=executor_id
        )

        await client_executor.send_message(
            chat_id=executor_id,
            text=f'Вы взяли задание: {card["name"]}',
        )

    return {"success": True}


async def download_kaiten_files(task_id: int, file_names: list[str]) -> list[bytes]:
    """
    Скачать файлы карточки по именам (через локальное файловое хранилище).
    """
    if not task_id or not file_names:
        return []

    downloaded_files = []

    try:
        response = await brain_client.list_files(str(task_id))
        
        if not response or not response.get('files'):
            return []
        
        files_list = response['files']
        
        for file_ref in file_names:
            # Попытаемся найти по id, затем по имени
            match = next((f for f in files_list if str(f.get('id')) == str(file_ref)), None)
            if match:
                file_id = match.get('id')
            else:
                target_file = next((f for f in files_list if f.get('original_filename') == file_ref or f.get('name') == file_ref), None)
                if not target_file:
                    continue
                file_id = target_file.get('id')

            if not file_id:
                continue

            file_data, dl_status = await brain_client.download_file(str(file_id))

            if dl_status == 200 and isinstance(file_data, bytes):
                downloaded_files.append(file_data)

    except Exception as e:
        print(f"Error downloading files: {e}")

    return downloaded_files


async def send_complete_preview(card_id: str, client_key: str) -> dict:
    """
    Отправить превью поста в complete_topic.
    Отправляет сообщение с картинками и отформатированным текстом поста,
    затем отправляет название задачи, имя клиента и дату отправки.
    
    Args:
        card_id: ID карточки
        client_key: Ключ клиента для которого создаётся превью
        
    Returns:
        dict с success, post_id и info_id (или error)
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
    
    # Получаем контент для клиента (сначала специфичный, потом общий)
    content_dict = card.get("content", {})
    if isinstance(content_dict, dict):
        content = content_dict.get(client_key) or content_dict.get('all', '')
    else:
        # Обратная совместимость со старым форматом
        content = content_dict if isinstance(content_dict, str) else ''

    tags = card.get("tags", [])

    post_text = generate_post(
        content=content,
        tags=tags,
        client_key=client_key
    )

    # Загружаем изображения если есть
    task_id = card.get("task_id")
    post_images = card.get("post_images", []) or []
    
    downloaded_images = []
    if task_id and post_images:
        downloaded_images = await download_kaiten_files(task_id, post_images)
    
    post_id = None
    post_ids = []  # Список всех ID сообщений для медиа-групп
    
    try:
        # Отправляем пост с изображениями или без
        if downloaded_images:
            if len(downloaded_images) == 1:
                result = await client_executor.send_photo(
                    chat_id=group_forum,
                    photo=downloaded_images[0],
                    caption=post_text,
                    parse_mode="HTML",
                    reply_to_message_id=complete_topic
                )
                if result.get("success"):
                    post_id = result.get("message_id")
                    post_ids = [post_id]
            else:
                result = await client_executor.send_media_group(
                    chat_id=group_forum,
                    media=downloaded_images,
                    caption=post_text,
                    parse_mode="HTML",
                    reply_to_message_id=complete_topic
                )
                if result.get("success"):
                    post_id = result.get("message_id")
                    post_ids = result.get("message_ids", [post_id])  # Сохраняем все ID
        else:
            result = await client_executor.send_message(
                chat_id=group_forum,
                text=post_text,
                reply_to_message_id=complete_topic,
                parse_mode="HTML"
            )
            if result.get("success"):
                post_id = result.get("message_id")
                post_ids = [post_id]
        
        if not post_id:
            return {"error": f"Failed to send preview: {result.get('error', 'Unknown error')}", "success": False}
        
        # Получаем и отправляем entities (опросы и др.)
        entities_result = await get_entities_for_client(card_id, client_key)
        if entities_result.get('success') and entities_result.get('entities'):
            entities = entities_result['entities']
            for entity in entities:
                entity_type = entity.get('type')
                entity_data = entity.get('data', {})
                
                if entity_type == 'poll':
                    poll_result = await send_poll_preview(
                        bot=client_executor.bot,
                        chat_id=group_forum,
                        entity_data=entity_data,
                        reply_to_message_id=complete_topic
                    )
                    if poll_result.get('success'):
                        entity_msg_id = poll_result.get('message_id')
                        if entity_msg_id:
                            post_ids.append(entity_msg_id)
        
        # Формируем дату отправки
        send_time = card.get("send_time")
        date_str = "Не указана"
        if send_time:
            try:
                dt = datetime.fromisoformat(send_time)
                date_str = dt.strftime('%d.%m.%Y %H:%M')
            except:
                pass
        
        # Получаем исполнителя и редактора
        executor_name = "Не назначен"
        editor_name = "Не назначен"
        
        executor_id = card.get('executor_id')
        if executor_id:
            users = await get_users(user_id=executor_id)
            if users:
                user = users[0]
                tg_user = await get_telegram_user(
                    bot=client_executor.bot,
                    telegram_id=user.get("telegram_id")
                )
                if tg_user:
                    executor_name = f'@{tg_user.username}' if tg_user.username else tg_user.full_name
        
        editor_id = card.get('editor_id')
        if editor_id:
            users = await get_users(user_id=editor_id)
            if users:
                user = users[0]
                tg_user = await get_telegram_user(
                    bot=client_executor.bot,
                    telegram_id=user.get("telegram_id")
                )
                if tg_user:
                    editor_name = f'@{tg_user.username}' if tg_user.username else tg_user.full_name
        
        # Отправляем информацию о задаче и клиенте
        card_name = card.get("name", "Без названия")
        info_text = (
            f"✅ Готовый пост для задачи <b>{card_name}</b> для клиента <b>{client_label}</b>\n"
            f"📅 Дата отправки: <b>{date_str}</b>\n"
            f"👤 Исполнитель: <code>{executor_name}</code>\n"
            f"✏️ Редактор: <code>{editor_name}</code>"
        )
        
        info_result = await client_executor.send_message(
            chat_id=group_forum,
            text=info_text,
            reply_to_message_id=complete_topic,
            parse_mode="HTML"
        )
        
        info_id = info_result.get("message_id") if info_result.get("success") else None
        
        return {"success": True, 
                "post_id": post_id, 
                "post_ids": post_ids, 
                "info_id": info_id
                }
    
    except Exception as e:
        return {"error": str(e), "success": False}


async def update_complete_preview(card_id: str, client_key: str, post_id: int, 
                                   info_id: int | None = None,
                                   post_ids: list[int] | None = None) -> dict:
    """
    Обновить превью поста в complete_topic.
    
    Args:
        card_id: ID карточки
        client_key: Ключ клиента
        post_id: ID сообщения с постом для обновления
        info_id: ID информационного сообщения для обновления
        post_ids: Список всех ID сообщений (для медиа-групп)
        
    Returns:
        dict с success, post_id и info_id (или error)
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
    
    # Получаем контент для клиента (сначала специфичный, потом общий)
    content_dict = card.get("content", {})
    if isinstance(content_dict, dict):
        content = content_dict.get(client_key) or content_dict.get('all', '')
    else:
        # Обратная совместимость со старым форматом
        content = content_dict if isinstance(content_dict, str) else ''

    tags = card.get("tags", [])

    post_text = generate_post(
        content=content,
        tags=tags,
        client_key=client_key
    )
    
    new_post_id = post_id
    new_info_id = info_id
    
    try:
        # Пытаемся обновить сообщение с постом
        # Примечание: media group нельзя редактировать, только текст/caption
        result = await client_executor.edit_message(
            chat_id=group_forum,
            message_id=str(post_id),
            text=post_text,
            parse_mode="HTML"
        )
        
        if not result.get("success"):
            # Если редактирование не удалось (например, это media group),
            # удаляем все старые сообщения и отправляем новые
            
            # Удаляем все сообщения медиа-группы
            ids_to_delete = post_ids if post_ids else [post_id]
            for msg_id in ids_to_delete:
                try:
                    await client_executor.delete_message(
                        chat_id=group_forum,
                        message_id=str(msg_id)
                    )
                except Exception as e:
                    print(f"Error deleting message {msg_id}: {e}")
            
            # Удаляем info сообщение
            if info_id:
                try:
                    await client_executor.delete_message(
                        chat_id=group_forum,
                        message_id=str(info_id)
                    )
                except Exception as e:
                    print(f"Error deleting info message {info_id}: {e}")
            
            new_preview = await send_complete_preview(card_id, client_key)
            return new_preview
        
        # Обновляем или создаём entities
        new_post_ids = [new_post_id]
        entities_result = await get_entities_for_client(card_id, client_key)
        if entities_result.get('success') and entities_result.get('entities'):
            entities = entities_result['entities']
            for entity in entities:
                entity_type = entity.get('type')
                entity_data = entity.get('data', {})
                
                if entity_type == 'poll':
                    poll_result = await send_poll_preview(
                        bot=client_executor.bot,
                        chat_id=group_forum,
                        entity_data=entity_data,
                        reply_markup=None
                    )
                    if poll_result.get('success'):
                        entity_msg_id = poll_result.get('message_id')
                        if entity_msg_id:
                            new_post_ids.append(entity_msg_id)
        
        # Обновляем информационное сообщение с датой
        if info_id:
            send_time = card.get("send_time")
            date_str = "Не указана"
            if send_time:
                try:
                    dt = datetime.fromisoformat(send_time)
                    date_str = dt.strftime('%d.%m.%Y %H:%M')
                except:
                    pass
            
            # Получаем исполнителя и редактора
            executor_name = "Не назначен"
            editor_name = "Не назначен"
            
            executor_id = card.get('executor_id')
            if executor_id:
                users = await get_users(user_id=executor_id)
                if users:
                    user = users[0]
                    tg_user = await get_telegram_user(
                        bot=client_executor.bot,
                        telegram_id=user.get("telegram_id")
                    )
                    if tg_user:
                        executor_name = f'@{tg_user.username}' if tg_user.username else tg_user.full_name
            
            editor_id = card.get('editor_id')
            if editor_id:
                users = await get_users(user_id=editor_id)
                if users:
                    user = users[0]
                    tg_user = await get_telegram_user(
                        bot=client_executor.bot,
                        telegram_id=user.get("telegram_id")
                    )
                    if tg_user:
                        editor_name = f'@{tg_user.username}' if tg_user.username else tg_user.full_name
            
            card_name = card.get("name", "Без названия")
            info_text = (
                f"✅ Готовый пост для задачи <b>{card_name}</b> для клиента <b>{client_label}</b>\n"
                f"📅 Дата отправки: <b>{date_str}</b>\n"
                f"👤 Исполнитель: <code>{executor_name}</code>\n"
                f"✏️ Редактор: <code>{editor_name}</code>"
            )
            
            info_result = await client_executor.edit_message(
                chat_id=group_forum,
                message_id=str(info_id),
                text=info_text,
                parse_mode="HTML"
            )
            
            if not info_result.get("success"):
                # Если не удалось обновить info, пересоздаём его
                await client_executor.delete_message(
                    chat_id=group_forum,
                    message_id=str(info_id)
                )
                new_info_result = await client_executor.send_message(
                    chat_id=group_forum,
                    text=info_text,
                    reply_to_message_id=complete_topic,
                    parse_mode="HTML"
                )
                if new_info_result.get("success"):
                    new_info_id = new_info_result.get("message_id")
        
        return {"success": True, "post_id": new_post_id, "post_ids": new_post_ids, "info_id": new_info_id}
    
    except Exception as e:
        return {"error": str(e), "success": False}


async def delete_complete_preview(post_id: int | None = None, 
                                  info_id: int | None = None, 
                                  post_ids: list[int] | None = None) -> dict:
    """
    Удалить превью поста из complete_topic.
    
    Args:
        post_id: ID сообщения с постом для удаления (старый формат)
        info_id: ID информационного сообщения для удаления
        post_ids: Список ID всех сообщений для удаления (новый формат для медиа-групп)
        
    Returns:
        dict с success (или error)
    """
    client_executor: TelegramExecutor = manager.get("telegram_executor")
    
    if not client_executor:
        return {"error": "Executor not found", "success": False}
    
    try:
        # Собираем все ID для удаления
        ids_to_delete = []
        
        # Новый формат - список post_ids
        if post_ids:
            ids_to_delete.extend(post_ids)
        # Старый формат - один post_id
        elif post_id:
            ids_to_delete.append(post_id)
        
        # Добавляем info_id
        if info_id:
            ids_to_delete.append(info_id)
        
        # Удаляем все сообщения
        for msg_id in ids_to_delete:
            try:
                await client_executor.delete_message(
                    chat_id=group_forum,
                    message_id=str(msg_id)
                )
            except Exception as e:
                print(f"Error deleting message {msg_id}: {e}")
        
        return {"success": True}
    
    except Exception as e:
        return {"error": str(e), "success": False}