
from datetime import datetime
from modules.card.card_events import on_executor
from modules.post_sender import download_files
from tg.main import TelegramExecutor
from modules.exec.executors_manager import manager
from modules.constants import SETTINGS, CLIENTS
from modules.post_generator import generate_post, render_post_from_card
from modules.enums import CardStatus
from modules.utils import get_telegram_user
from modules.entities_sender import send_poll_preview, get_entities_for_client
from app.models.card.Card import Card
from models.User import User
from app.models.Message import CardMessage
from modules.storage import download_file as _storage_download
from modules.json_utils import open_clients, open_settings

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

    cards = await Card.find(card_id=card_id)
    if not cards:
        return {"error": f"Card not found for {card_id}", "success": False}
    else:
        forum_messages = await CardMessage.filter_by(
            card_id=cards[0].card_id, message_type="forum"
        )

        first_or_none = forum_messages[0] if forum_messages else None

        message_id = first_or_none.message_id if first_or_none else None
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
    tags_raw = card.get("tags", []) if card.get("tags", []
                                            ) else ["Без тегов"]
    need_check = "✅" if card.get("need_check", False) else "❌"

    open_clients_dict = open_clients()
    settings = open_settings() or {}

    tags = []
    if tags_raw != ["Без тегов"]:
        # упорядочиваем теги по полю order из БД
        from modules.utils import sort_tags
        sorted_keys = await sort_tags(tags_raw)
        from modules.utils import get_tags_map
        tag_map = await get_tags_map()
        for t in sorted_keys:
            tag_label = '#' + tag_map.get(t, {}).get('tag', t)
            tags.append(tag_label)
    else:
        tags = ["Без тегов"]

    clients = []
    for client in card.get("clients", []):
        client_info = open_clients_dict.get(client, {})
        client_label = client_info.get("label", client)
        clients.append(f'<code>{client_label}</code>')
    if not clients:
        clients = ["Каналы не назначены"]

    if deadline != "Без дедлайна":
        try:
            dt = datetime.fromisoformat(deadline)
            deadline = dt.strftime('%d.%m.%Y %H:%M')
        except: pass

    days_ost = ''
    if deadline != "Без дедлайна":
        try:
            dt = datetime.fromisoformat(card.get("deadline"))
            delta = dt - datetime.now()
            days = delta.days
            days_ost = f' ({days} дн)'

        except Exception as e:
            print(f"Error calculating days remaining: {e}")

    data_list = []
    for i in ['executor_id', 'customer_id', 'editor_id']:

        _id = card.get(i)

        if _id is not None:
            users = await User.find(user_id=_id)
            user = users[0] if users else None

            if user is not None:
                tg_user = await get_telegram_user(
                    bot=client_executor.bot,
                    telegram_id=user.telegram_id
                )
                if tg_user:
                    username = f'@{tg_user.username}' if tg_user.username else f'`{tg_user.full_name}`'
                else:
                    username = f"ID: {card.get(i)}"
            else:
                username = f"ID: {card.get(i)} (ошибка получения)"
        else:
            username = "<code>Не назначен</code>"

        data_list.append(username)

    executor_nick, customer_nick, editor_nick = data_list

    text = (f'Статус: {tag}\n'
        f'\nНазвание: <code>{name}</code>'
        f'\nДедлайн: {deadline}{days_ost}'
        f'\n\n<b>🧪 Участники</b>'
        f'\nИсполнитель: {executor_nick}'
        f'\nЗаказчик: {customer_nick}'
        f'\nРедактор: {editor_nick}'
        f'\n\n<b>✨ Информация</b>'
        f'\nТеги: {", ".join(tags)}'
        f'\nКаналы: {", ".join(clients)}'
        f'\nПроверяемый: {need_check}'
        f'\n\n<b>⚡ Описание</b>'
        f'\n<blockquote>{description[:1024]}</blockquote>'
    )

    return text

async def forum_message(card_id: str):
    """Отправить сообщение в форум о новой карточке и обновить карточку с ID сообщения"""

    client_executor: TelegramExecutor = manager.get(
        "telegram_executor"
        )

    if not client_executor:
        return {"error": "Executor not found", "success": False}

    cards = await Card.find(card_id=card_id)
    if not cards:
        return {"error": "Card not found", "success": False}

    card = cards[0].to_full_dict()

    tag = pass_tag
    markup = []

    status = card['status']
    bot_username = (await client_executor.bot.get_me()).username
    view_link = f'https://t.me/{bot_username}?start=type-open-view_id-{card["card_id"]}'

    if status == CardStatus.pass_.value:
        markup = [
            {
                "text": "🤍 Забрать задание",
                "callback_data": "take_task",
                "ignore_row": True
            }
        ]

    elif status == CardStatus.edited.value:
        tag = edited_tag

        markup = [
            {
                "text": "💚 Задание взято",
                "callback_data": " ",
                "ignore_row": True
            },
            {
                "text": "👀 Просмотр задачи",
                "url": view_link,
                "ignore_row": True
            }
        ]
    
    elif status == CardStatus.review.value and card['editor_id'] is None:
        tag = needcheck_tag

        markup = [
            {
                "text": "💙 Взять на проверку",
                "callback_data": "edit_task",
                "ignore_row": True
            },
            {
                "text": "👀 Просмотр задачи",
                "url": view_link,
                "ignore_row": True
            }
        ]

    elif status == CardStatus.review.value:
        tag = checked_tag

        markup = [
            {
                "text": "💜 Задание на проверке",
                "callback_data": " ",
                "ignore_row": True
            },
            {
                "text": "👀 Просмотр задачи",
                "url": view_link,
                "ignore_row": True
            }
        ]

    elif status == CardStatus.ready.value:
        tag = done_tag

        markup = [
            {
                "text": "❤ Задание выполнено",
                "callback_data": " ",
                "ignore_row": True
            },
            {
                "text": "👀 Просмотр задачи",
                "url": view_link,
                "ignore_row": True
            }
        ]

    text = await text_getter(card, tag, client_executor)

    forum_messages = await CardMessage.filter_by(
        card_id=cards[0].card_id, message_type="forum"
    ) if cards else []

    first_or_none = forum_messages[0] if forum_messages else None

    if not first_or_none:

        data = await client_executor.send_message(
            reply_to_message_id=forum_topic,
            chat_id=group_forum,
            text=text,
            list_markup=markup,
            parse_mode="html"
        )

    else:
        data = await client_executor.edit_message(
            chat_id=group_forum,
            message_id=first_or_none.message_id,
            text=text,
            parse_mode="html",
            list_markup=markup
        )

        error = data.get("error", "")
        if 'not found' in error.lower():
            
            data = await client_executor.send_message(
                reply_to_message_id=forum_topic,
                chat_id=group_forum,
                text=text,
                list_markup=markup,
                parse_mode="html"
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

    users = await User.find(telegram_id=telegram_id)
    cards = await Card.find(card_id=card_id)
    if not cards:
        return {"error": "Card not found", "success": False}
    elif not users:
        return {"error": "User not found", "success": False}
    else:
        executor_id = str(users[0].user_id)

        await on_executor(executor_id, card_id=card_id)

    return {"success": True}


async def download_files_raw(file_ids: list[str]) -> list[bytes]:
    """
    Скачать файлы по их ID из БД и вернуть список raw bytes.
    """
    if not file_ids:
        return []

    downloaded_files: list[bytes] = []

    for file_ref in file_ids:
        try:
            file_id = str(file_ref)
            file_data, dl_status = await _storage_download(file_id)
            if dl_status == 200 and isinstance(file_data, (bytes, bytearray)):
                downloaded_files.append(bytes(file_data))
        except Exception as e:
            print(f"Error downloading file {file_ref}: {e}")

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
    
    cards = await Card.find(card_id=card_id)
    if not cards:
        return {"error": "Card not found", "success": False}

    card = cards[0].to_full_dict()

    client_config = CLIENTS.get(client_key)
    if not client_config:
        return {"error": f"Client {client_key} not found", "success": False}
    client_label = client_config.get('label', client_key)

    post_text = await render_post_from_card(card, client_key)

    # Загружаем изображения если есть
    post_images = card.get("post_images", []) or []
    
    downloaded_images = []
    if post_images:
        downloaded_images = await download_files(post_images)

    post_ids = []  # Список всех ID сообщений для медиа-групп
    entities_ids = []  # Список ID сущностей
    
    try:
        # Получаем entities для формирования клавиатуры
        entities_result = await get_entities_for_client(card_id, client_key)
        entities = entities_result.get('entities', []) if entities_result.get('success') else []
        
        # Формируем inline клавиатуру из entities типа inline_keyboard
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        reply_markup = None
        if entities:
            keyboard_buttons = []
            for entity in entities:
                if entity.get('type') == 'inline_keyboard':
                    entity_data = entity.get('data', {})
                    buttons = entity_data.get('buttons', [])
                    # Все кнопки из одного entity в одну строку
                    row = []
                    for btn in buttons:
                        text_btn = btn.get('text')
                        url = btn.get('url')
                        style = btn.get('style', None)
                        if text_btn and url:
                            row.append(InlineKeyboardButton(text=text_btn, url=url, style=style))
                    if row:
                        keyboard_buttons.append(row)
            
            if keyboard_buttons:
                reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        # Отправляем пост с изображениями или без
        if downloaded_images:
            if len(downloaded_images) == 1:
                result = await client_executor.send_photo(
                    chat_id=group_forum,
                    photo=downloaded_images[0]['data'],
                    caption=post_text,
                    parse_mode="HTML",
                    reply_to_message_id=complete_topic,
                    has_spoiler=downloaded_images[0].get('hide', False),
                    reply_markup=reply_markup
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
                    
                    # Для media group добавляем клавиатуру отдельным сообщением
                    if reply_markup:
                        keyboard_result = await client_executor.send_message(
                            chat_id=group_forum,
                            text="🔗",
                            reply_markup=reply_markup,
                            reply_to_message_id=complete_topic
                        )
                        if keyboard_result.get("success"):
                            post_ids.append(keyboard_result.get("message_id"))
        else:
            result = await client_executor.send_message(
                chat_id=group_forum,
                text=post_text,
                reply_to_message_id=complete_topic,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            if result.get("success"):
                post_id = result.get("message_id")
                post_ids = [post_id]
        
        if not post_id:
            return {"error": 
                f"Failed to send preview: {result.get('error', 'Unknown error')}", 
                "success": False}
        
        # Отправляем entities (опросы и др.) - inline_keyboard уже обработан выше
        for entity in entities:
            entity_type = entity.get('type')
            
            # inline_keyboard уже обработан выше
            if entity_type == 'inline_keyboard':
                continue
            
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
                            entities_ids.append(entity_msg_id)
        
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
            users = await User.find(user_id=executor_id)
            if users:
                user = users[0]
                tg_user = await get_telegram_user(
                    bot=client_executor.bot,
                    telegram_id=user.telegram_id
                )
                if tg_user:
                    executor_name = f'@{tg_user.username}' if tg_user.username else tg_user.full_name
        
        editor_id = card.get('editor_id')
        if editor_id:
            users = await User.find(user_id=editor_id)
            if users:
                user = users[0]
                tg_user = await get_telegram_user(
                    bot=client_executor.bot,
                    telegram_id=user.telegram_id
                )
                if tg_user:
                    editor_name = f'@{tg_user.username}' if tg_user.username else tg_user.full_name
        
        # Отправляем информацию о задаче и клиенте
        card_name = card.get("name", "Без названия")
        
        # Получаем настройки для клиента
        settings_text = ""
        clients_settings = card.get("clients_settings", {})
        if isinstance(clients_settings, dict):
            client_settings = clients_settings.get(client_key, {})
            if isinstance(client_settings, dict) and client_settings:
                settings_lines = []
                for key, value in client_settings.items():
                    # Форматируем ключ (заменяем _ на пробел, капитализируем)
                    formatted_key = key.replace('_', ' ').capitalize()
                    settings_lines.append(f"  • <code>{formatted_key}</code>: {value}")
                if settings_lines:
                    settings_text = "\n<b>⚙️ Настройки:</b>\n" + "\n".join(settings_lines)
        
        info_text = (
            f"✅ Готовый пост для задачи <b>{card_name}</b> для клиента <b>{client_label}</b>\n"
            f"📅 Дата отправки: <b>{date_str}</b>\n"
            f"👤 Исполнитель: <code>{executor_name}</code>\n"
            f"✏️ Редактор: <code>{editor_name}</code>"
            f"{settings_text}"
        )
        
        info_result = await client_executor.send_message(
            chat_id=group_forum,
            text=info_text,
            reply_to_message_id=complete_topic,
            parse_mode="HTML"
        )
        
        info_id = info_result.get("message_id") if info_result.get("success") else None
        
        return {"success": True, 
                "post_ids": post_ids,
                "entities": entities_ids,
                "info_id": info_id
                }

    except Exception as e:
        return {"error": str(e), "success": False}


async def update_complete_preview(card_id: str, client_key: str,
                                  post_ids: list[int] | None = None,
                                  info_id: int | None = None,
                                  entities: list[int] | None = None
                                  ) -> dict:
    """
    Обновить превью поста в complete_topic.
    
    Args:
        card_id: ID карточки
        client_key: Ключ клиента
    Returns:
        dict с success и info_id (или error)
    """
    client_executor: TelegramExecutor = manager.get("telegram_executor")

    if not client_executor:
        return {"error": "Executor not found", "success": False}

    cards = await Card.find(card_id=card_id)
    if not cards:
        return {"error": "Card not found", "success": False}

    card = cards[0].to_full_dict()

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

    post_text = await render_post_from_card(card, client_key)

    new_info_id = info_id
    
    try:
        # Пытаемся обновить сообщение с постом
        # Примечание: media group нельзя редактировать, только текст/caption
        result = await client_executor.edit_message(
            chat_id=group_forum,
            message_id=str(post_ids[0]) if post_ids else None,
            text=post_text,
            parse_mode="HTML"
        )
        
        if not result.get("success"):
            # Если редактирование не удалось (например, это media group),
            # удаляем все старые сообщения и отправляем новые
            
            # Удаляем все сообщения медиа-группы
            for msg_id in post_ids:
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
        new_post_id = result.get('message_id')
        new_post_ids = [new_post_id] if new_post_id else []
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
                users = await User.find(user_id=executor_id)
                if users:
                    user = users[0]
                    tg_user = await get_telegram_user(
                        bot=client_executor.bot,
                        telegram_id=user.telegram_id
                    )
                    if tg_user:
                        executor_name = f'@{tg_user.username}' if tg_user.username else tg_user.full_name
            
            editor_id = card.get('editor_id')
            if editor_id:
                users = await User.find(user_id=editor_id)
                if users:
                    user = users[0]
                    tg_user = await get_telegram_user(
                        bot=client_executor.bot,
                        telegram_id=user.telegram_id
                    )
                    if tg_user:
                        editor_name = f'@{tg_user.username}' if tg_user.username else tg_user.full_name

            card_name = card.get("name", "Без названия")

            # Получаем настройки для клиента
            settings_text = ""
            clients_settings = card.get("clients_settings", {})
            if isinstance(clients_settings, dict):
                client_settings = clients_settings.get(client_key, {})
                if isinstance(client_settings, dict) and client_settings:
                    settings_lines = []
                    for key, value in client_settings.items():
                        # Форматируем ключ (заменяем _ на пробел, капитализируем)
                        formatted_key = key.replace('_', ' ').capitalize()
                        settings_lines.append(f"  • <code>{formatted_key}</code>: {value}")
                    if settings_lines:
                        settings_text = "\n<b>⚙️ Настройки:</b>\n" + "\n".join(settings_lines)
            
            info_text = (
                f"✅ Готовый пост для задачи <b>{card_name}</b> для клиента <b>{client_label}</b>\n"
                f"📅 Дата отправки: <b>{date_str}</b>\n"
                f"👤 Исполнитель: <code>{executor_name}</code>\n"
                f"✏️ Редактор: <code>{editor_name}</code>"
                f"{settings_text}"
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
        
        return {"success": True, "post_ids": new_post_ids, "info_id": new_info_id}
    
    except Exception as e:
        return {"error": str(e), "success": False}


async def delete_complete_preview(info_ids: list[int] | None = None,
                                  post_ids: list[int] | None = None,
                                  entities: list[int] | None = None
                                  ) -> dict:
    """
    Удалить превью поста из complete_topic.
    
    Args:
        info_id: ID информационного сообщения для удаления
        post_ids: Список ID всех сообщений для удаления
        entities: Список ID сущностей для удаления

    Returns:
        dict с success (или error)
    """
    client_executor: TelegramExecutor = manager.get("telegram_executor")
    
    if not client_executor:
        return {"error": "Executor not found", "success": False}

    print(entities, info_ids, post_ids)

    try:
        ids_to_delete = []

        if post_ids:
            ids_to_delete.extend(post_ids)

        if entities:
            ids_to_delete.extend(entities)

        if info_ids:
            ids_to_delete.extend(info_ids)

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