
from datetime import datetime
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
                    username = f"ID: {card.get(i)}"
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
        f'\n{description[:750]}'
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
    markup = []

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
    
    print(card.get("forum_message_id", None))

    if card.get("forum_message_id", None):

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

        error = data.get("error", "")
        if 'not found' in error.lower():
            return {
                "error": f"Не удалость найти сообщение в форуме. Error: {error}", 
                "success": False
            }

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
    
    # Генерируем текст поста
    content = card.get("content") or card.get("description") or ""
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
        
        # Формируем дату отправки
        send_time = card.get("send_time")
        date_str = "Не указана"
        if send_time:
            try:
                dt = datetime.fromisoformat(send_time)
                date_str = dt.strftime('%d.%m.%Y %H:%M')
            except:
                pass
        
        # Отправляем информацию о задаче и клиенте
        card_name = card.get("name", "Без названия")
        info_text = f"✅ Готовый пост для задачи <b>{card_name}</b> для клиента <b>{client_label}</b>\n📅 Дата отправки: <b>{date_str}</b>"
        
        info_result = await client_executor.send_message(
            chat_id=group_forum,
            text=info_text,
            reply_to_message_id=complete_topic,
            parse_mode="HTML"
        )
        
        info_id = info_result.get("message_id") if info_result.get("success") else None
        
        return {"success": True, "post_id": post_id, "post_ids": post_ids, "info_id": info_id}
    
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
    
    # Генерируем текст поста
    content = card.get("content") or card.get("description") or ""
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
            
            card_name = card.get("name", "Без названия")
            info_text = f"✅ Готовый пост для задачи <b>{card_name}</b> для клиента <b>{client_label}</b>\n📅 Дата отправки: <b>{date_str}</b>"
            
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
        
        return {"success": True, "post_id": new_post_id, "post_ids": [new_post_id], "info_id": new_info_id}
    
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