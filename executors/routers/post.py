"""
Роутер для управления публикацией постов через различных исполнителей.
Вся логика работы с исполнителями и генерацией контента находится здесь.
"""
from typing import Optional
import time
import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from modules.executors_manager import manager
from modules.constants import CLIENTS
from modules.logs import executors_logger as logger
from modules.post_generator import generate_post
from modules.post_sender import download_files
from modules.entities_sender import send_poll_preview
from tg.main import TelegramExecutor
from vk.main import VKExecutor

router = APIRouter(prefix="/post", tags=["Post"])

class PostSendRequest(BaseModel):
    """Запрос на немедленную отправку поста"""
    card_id: str
    client_key: str
    content: str  # Сырой контент
    tags: Optional[list[str]] = None
    post_images: Optional[list[str]] = None  # Список имён файлов
    settings: dict = {}  # Дополнительные настройки для отправки
    entities: Optional[list[dict]] = None  # Entities для отправки (опросы и т.д.)


def get_client_config(client_key: str) -> tuple:
    """
    Получить конфигурацию клиента и исполнителя.
    
    Returns:
        tuple: (client_config, executor_name, client_id)
    """
    client_config = CLIENTS.get(client_key)
    if not client_config:
        raise HTTPException(status_code=404, detail=f"Client {client_key} not found")

    executor_name = client_config.get('executor_name') or client_config.get('executor')
    client_id = client_config.get('client_id')

    if not executor_name or not client_id:
        raise HTTPException(status_code=400, detail=f"Incomplete client configuration for {client_key}")

    return client_config, executor_name, client_id

@router.post("/send")
async def send_post(request: PostSendRequest):
    """
    Немедленно отправить пост.
    Используется для telegram_executor и vk_executor.

    Генерация контента происходит здесь, на стороне executors.
    Поддерживает отправку нескольких фото (media group).
    """

    # Инициализация лога действий и таймера
    overall_start = time.perf_counter()
    action_log: list[dict] = []

    def add_log(action: str, message: str = "", level: str = "info", duration_ms: float | None = None, **extra):
        entry = {
            "time": datetime.datetime.utcnow().isoformat() + "Z",
            "action": action,
            "level": level,
            "message": message
        }
        if duration_ms is not None:
            try:
                entry["duration_ms"] = str(int(duration_ms))
            except Exception:
                entry["duration_ms"] = str(duration_ms)
        if extra:
            entry.update(extra)
        action_log.append(entry)
        logger_method = getattr(logger, level, logger.info)
        logger_method(f"{action}: {message} | " + " | ".join(f"{k}={v}" for k, v in extra.items()))

    add_log("start", f"Начало отправки поста {request.card_id} для клиента {request.client_key}")

    # Получаем конфигурацию клиента
    client_config, executor_name, client_id = get_client_config(request.client_key)

    # Получаем исполнителя
    executor = manager.get(executor_name)
    if not executor:
        add_log("executor_missing", f"Исполнитель {executor_name} не найден", level="error")
        return {"success": False, "error": f"Исполнитель {executor_name} не найден", "logs": action_log}

    try:
        # Генерируем текст поста с замером времени
        gen_start = time.perf_counter()
        post_text = generate_post(
            content=request.content,
            tags=request.tags,
            client_key=request.client_key
        )
        gen_end = time.perf_counter()
        add_log("generate_post", "Сгенерирован текст поста", duration_ms=(gen_end - gen_start) * 1000, length=len(post_text))

        # Преобразуем client_id
        try:
            chat_id = int(client_id)
        except ValueError:
            chat_id = client_id
        add_log("client_id_parsed", f"Преобразован client_id -> {chat_id}")

        result = None

        # Получаем имена файлов для отправки
        post_image_names = request.post_images or []

        # Скачиваем файлы по ID из БД если есть (замер времени)
        downloaded_files = []
        if post_image_names:
            dl_start = time.perf_counter()
            downloaded_files = await download_files(post_image_names)
            dl_end = time.perf_counter()
            add_log("download_files", 
                    f"Скачано {len(downloaded_files)} файлов из БД", duration_ms=(dl_end - dl_start) * 1000, files_count=len(downloaded_files))

        # Обработка для VK
        if isinstance(executor, VKExecutor):
            attachments = []
            if downloaded_files:
                add_log("vk_upload_start", f"Начало загрузки {len(downloaded_files)} файлов в VK")

                import tempfile
                import os as os_module

                for idx, file_info in enumerate(downloaded_files):
                    file_type = file_info.get('type')
                    file_name = file_info.get('name')
                    file_size = len(file_info.get('data', b""))

                    add_log("vk_file_process", 
                            f"Обработка файла {idx + 1}/{len(downloaded_files)}", file_name=file_name, file_type=file_type, size=file_size)

                    # Сохраняем во временный файл для загрузки
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_name}") as tmp_file:
                        tmp_file.write(file_info['data'])
                        tmp_path = tmp_file.name
                    add_log("tmp_file_saved", "Временный файл сохранён", tmp_path=tmp_path)

                    try:
                        upload_start = time.perf_counter()
                        if file_type == 'photo':
                            upload_result = await executor.upload_photo_to_wall(tmp_path)
                        elif file_type == 'video':
                            upload_result = await executor.upload_video_to_wall(tmp_path)
                        else:
                            add_log("vk_unsupported_type", f"Неподдерживаемый тип файла: {file_type}", level="warning")
                            continue
                        upload_end = time.perf_counter()

                        add_log("vk_upload_result", 
                                f"Результат загрузки для {file_name}", 
                                duration_ms=(upload_end - upload_start) * 1000, result=upload_result)

                        if upload_result.get('success') and upload_result.get('attachment'):
                            attachments.append(upload_result['attachment'])
                            add_log("vk_attachment_added", 
                                    "Вложение добавлено", attachment=upload_result.get('attachment'))
                        else:
                            add_log("vk_upload_error", f"Ошибка загрузки {file_name}", level="error", error=upload_result.get('error'))

                    finally:
                        try:
                            os_module.unlink(tmp_path)
                            add_log("tmp_file_removed", "Временный файл удалён", tmp_path=tmp_path)
                        except Exception as ex_rm:
                            add_log("tmp_remove_error", f"Не удалось удалить временный файл: {ex_rm}", level="warning")

                add_log("vk_attachments_count", f"Подготовлено вложений: {len(attachments)}", count=len(attachments))

            image_view_setting = request.settings.get('image_view', 'grid')
            post_start = time.perf_counter()
            result = await executor.create_wall_post(
                text=post_text,
                attachments=attachments if attachments else None,
                primary_attachments_mode=image_view_setting
            )
            post_end = time.perf_counter()

            add_log("vk_create_post", "Создание поста в VK", duration_ms=(post_end - post_start) * 1000, result=result)

        # Обработка для Telegram
        elif isinstance(executor, TelegramExecutor):
            # Формируем inline клавиатуру из entities типа inline_keyboard
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            reply_markup = None
            if request.entities:
                keyboard_buttons = []
                for entity in request.entities:
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

            # collect sent message ids (main + entities) for optional forwarding
            sent_message_ids: list[int] = []
            main_message_id = None
            keyboard_message_id: int | None = None
            is_media_group = False

            if downloaded_files:
                if len(downloaded_files) == 1:
                    file_info = downloaded_files[0]
                    ftype = file_info.get('type')
                    has_spoiler = file_info.get('hide', False)

                    if ftype == 'photo':
                        send_start = time.perf_counter()
                        result = await executor.send_photo(chat_id=str(chat_id), 
                                                           photo=file_info['data'], caption=post_text, has_spoiler=has_spoiler, reply_markup=reply_markup)
                        send_end = time.perf_counter()

                        add_log('tg_send_photo', 'Отправлено фото', duration_ms=(send_end - send_start) * 1000, file_name=file_info.get('name'))

                    elif ftype == 'video':
                        send_start = time.perf_counter()
                        result = await executor.send_video(
                            chat_id=str(chat_id), 
                            video=file_info['data'], 
                            caption=post_text, 
                            reply_markup=reply_markup
                        )
                        send_end = time.perf_counter()

                        add_log('tg_send_video', 
                                'Отправлено видео', duration_ms=(send_end - send_start) * 1000, file_name=file_info.get('name'))

                    else:
                        send_start = time.perf_counter()
                        result = await executor.send_document(
                            chat_id=str(chat_id), document=file_info['data'], caption=post_text, reply_markup=reply_markup)
                        send_end = time.perf_counter()

                        add_log('tg_send_document', 
                                'Отправлен документ', duration_ms=(send_end - send_start) * 1000, file_name=file_info.get('name'))

                    # collect single-message id
                    if result and result.get('success') and result.get('message_id'):
                        main_message_id = result.get('message_id')
                        sent_message_ids.append(main_message_id)

                else:
                    send_start = time.perf_counter()
                    result = await executor.send_media_group(
                        chat_id=str(chat_id), 
                        media=downloaded_files, 
                        caption=post_text
                        )
                    send_end = time.perf_counter()
    
                    add_log('tg_send_media_group', 'Отправлена медиагруппа', 
                            duration_ms=(send_end - send_start) * 1000, files_count=len(downloaded_files))

                    is_media_group = True

                    # collect media_group message ids (preserve actual send order: media messages first)
                    if result and result.get('success'):
                        group_ids = result.get('message_ids') or []
                        if group_ids:
                            main_message_id = result.get('message_id')
                            sent_message_ids.extend(group_ids)

                    # Для media group добавляем клавиатуру отдельным сообщением
                    keyboard_message_id = None
                    if reply_markup:
                        keyboard_start = time.perf_counter()
                        keyboard_result = await executor.send_message(
                            chat_id=str(chat_id),
                            text="🔗",
                            reply_markup=reply_markup
                        )
                        keyboard_end = time.perf_counter()
                        add_log('tg_send_keyboard', 'Отправлена клавиатура к media group',
                                duration_ms=(keyboard_end - keyboard_start) * 1000, result=keyboard_result)
                        if keyboard_result and keyboard_result.get('success') and keyboard_result.get('message_id'):
                            keyboard_message_id = keyboard_result.get('message_id')
                            sent_message_ids.append(keyboard_message_id)

            else:
                send_start = time.perf_counter()
                result = await executor.send_message(chat_id=str(chat_id), text=post_text, reply_markup=reply_markup)
                send_end = time.perf_counter()
                add_log('tg_send_message', 
                        'Отправлено текстовое сообщение', duration_ms=(send_end - send_start) * 1000)

                if result and result.get('success') and result.get('message_id'):
                    main_message_id = result.get('message_id')
                    sent_message_ids.append(main_message_id)

        # Результат отправки
        if result and result.get('success'):
            add_log('sent', f"Пост успешно отправлен для карточки {request.card_id}, клиента {request.client_key}, файлов: {len(downloaded_files)}", files_sent=len(downloaded_files))

            # Отправляем entities если они есть (polls и т.д.) - inline_keyboard уже обработан выше
            if request.entities and isinstance(executor, TelegramExecutor):
                for entity in request.entities:
                    try:
                        entity_type = entity.get('type')
                        
                        # inline_keyboard уже обработан выше
                        if entity_type == 'inline_keyboard':
                            continue
                        
                        if entity_type == 'poll':
                            entity_data = entity.get('data', {})

                            ent_start = time.perf_counter()
                            poll_result = await send_poll_preview(
                                bot=executor.bot, chat_id=chat_id, entity_data=entity_data, 
                                reply_markup=None
                                )
                            ent_end = time.perf_counter()

                            if poll_result.get('success'):
                                add_log('entity_send', 
                                        f"Сущность {entity.get('id')} отправлена", 
                                        duration_ms=(ent_end - ent_start) * 1000, 
                                        entity_type='poll', result=poll_result
                                        )
                                # collect entity message id for possible forwarding
                                if poll_result.get('message_id'):
                                    sent_message_ids.append(poll_result.get('message_id'))
                            else:
                                add_log('entity_send_failed', 
                                        f"Не удалось отправить сущность {entity.get('id')}: {poll_result.get('error')}", 
                                        level='error',
                                        entity_type='poll'
                                        )
                        else:
                            add_log('entity_skip', f"Неподдерживаемый тип сущности: {entity_type}", level='warning')
                    except Exception as e:
                        add_log('entity_error', f"Ошибка при отправке сущности: {e}", level='error')

            # Forwarding: if forward_to is set in client settings — forward messages to target clients
            forward_list = request.settings.get('forward_to') if isinstance(request.settings, dict) else None
            only_main = request.settings.get('only_main_message', True) if isinstance(request.settings, dict) else True

            if forward_list and isinstance(forward_list, list) and sent_message_ids:
                # choose which message ids to forward
                if only_main:
                    to_forward = []
                    if main_message_id:
                        to_forward = [main_message_id]
                    elif sent_message_ids:
                        to_forward = [sent_message_ids[0]]
                else:
                    to_forward = list(dict.fromkeys(sent_message_ids))  # unique preserve order

                if to_forward:
                    for tgt in forward_list:
                        # skip if target is the same client
                        if tgt == request.client_key:
                            continue

                        tgt_conf = CLIENTS.get(tgt)
                        if not tgt_conf:
                            add_log('tg_forward_skip', f'Client not found: {tgt}', level='warning')
                            continue

                        tgt_executor = tgt_conf.get('executor_name') or tgt_conf.get('executor')
                        # only support Telegram->Telegram forwarding for now
                        if tgt_executor != 'telegram_executor':
                            add_log('tg_forward_skip', f'Unsupported target executor for {tgt}: {tgt_executor}', level='warning')
                            continue

                        tgt_chat_id = tgt_conf.get('client_id')
                        try:
                            # Special-case: original post was a media-album and user asked to forward all messages ->
                            # re-send the album as a single media_group to the target (better than forwarding messages one-by-one),
                            # then re-send the keyboard message (inline keyboard won't be preserved by forward_message).
                            if is_media_group and (not only_main) and sent_message_ids:
                                # Forward only the first photo of the album (use forward_message per requirement)
                                # find group ids if available (fallback to sent_message_ids ordering)
                                try:
                                    _group_ids = group_ids
                                except NameError:
                                    _group_ids = [mid for mid in sent_message_ids if keyboard_message_id is None or mid != keyboard_message_id]

                                first_media_id = None
                                if _group_ids:
                                    first_media_id = _group_ids[0]
                                else:
                                    for mid in to_forward:
                                        if keyboard_message_id and mid == keyboard_message_id:
                                            continue
                                        first_media_id = mid
                                        break

                                # forward the first media message
                                if first_media_id:
                                    try:
                                        fwd_start = time.perf_counter()
                                        fwd_msg = await executor.bot.forward_message(
                                            chat_id=str(tgt_chat_id),
                                            from_chat_id=str(chat_id),
                                            message_id=first_media_id
                                        )
                                        fwd_end = time.perf_counter()
                                        add_log('tg_forward_first_media', f'Forwarded first media to {tgt}', duration_ms=(fwd_end - fwd_start) * 1000,
                                                target=tgt, forwarded_message_id=getattr(fwd_msg, 'message_id', None))
                                    except Exception as e:
                                        add_log('tg_forward_failed', f'Failed to forward first media to {tgt}: {e}', level='error', target=tgt)

                                # forward keyboard message as a forward (so it appears in target)
                                if keyboard_message_id:
                                    try:
                                        kb_fwd_start = time.perf_counter()
                                        kb_fwd_msg = await executor.bot.forward_message(
                                            chat_id=str(tgt_chat_id),
                                            from_chat_id=str(chat_id),
                                            message_id=keyboard_message_id
                                        )
                                        kb_fwd_end = time.perf_counter()
                                        add_log('tg_forward_keyboard', f'Forwarded keyboard message to {tgt}', duration_ms=(kb_fwd_end - kb_fwd_start) * 1000,
                                                target=tgt, forwarded_message_id=getattr(kb_fwd_msg, 'message_id', None))
                                    except Exception as e:
                                        add_log('tg_forward_failed', f'Failed to forward keyboard to {tgt}: {e}', level='warning', target=tgt)

                                # Forward remaining entity messages (polls etc.) that are not part of the album or keyboard
                                for pending_id in to_forward:
                                    # skip other album items and already-forwarded ids
                                    if (_group_ids and pending_id in _group_ids) or (keyboard_message_id and pending_id == keyboard_message_id) or (pending_id == first_media_id):
                                        continue
                                    try:
                                        ent_fwd_start = time.perf_counter()
                                        ent_fwd_msg = await executor.bot.forward_message(
                                            chat_id=str(tgt_chat_id),
                                            from_chat_id=str(chat_id),
                                            message_id=pending_id
                                        )
                                        ent_fwd_end = time.perf_counter()
                                        add_log('tg_forward_entity', f'Forwarded entity to {tgt}', duration_ms=(ent_fwd_end - ent_fwd_start) * 1000,
                                                target=tgt, forwarded_message_id=getattr(ent_fwd_msg, 'message_id', None))
                                    except Exception as e:
                                        add_log('tg_forward_failed', f'Failed to forward entity to {tgt}: {e}', level='error', target=tgt)
                            else:
                                # Per-message forwarding: forward messages in original order.
                                for msg_id in to_forward:
                                    # if this id is the keyboard message — re-send it to preserve markup
                                    if msg_id == keyboard_message_id and reply_markup:
                                        kb_start = time.perf_counter()
                                        kb_res = await executor.send_message(
                                            chat_id=str(tgt_chat_id),
                                            text="🔗",
                                            reply_markup=reply_markup
                                        )
                                        kb_end = time.perf_counter()
                                        add_log('tg_forward_keyboard', f'Re-sent keyboard to {tgt}', duration_ms=(kb_end - kb_start) * 1000,
                                                target=tgt, result=kb_res)
                                    else:
                                        fwd_start = time.perf_counter()
                                        fwd_msg = await executor.bot.forward_message(
                                            chat_id=str(tgt_chat_id),
                                            from_chat_id=str(chat_id),
                                            message_id=msg_id
                                        )
                                        fwd_end = time.perf_counter()

                                        add_log('tg_forward', f'Forwarded to {tgt}', duration_ms=(fwd_end - fwd_start) * 1000,
                                                target=tgt, forwarded_message_id=getattr(fwd_msg, 'message_id', None))
                        except Exception as e:
                            add_log('tg_forward_failed', f'Failed to forward to {tgt}: {e}', level='error', target=tgt)

            if request.settings.get('auto_pin', True):
                if result and result.get('success'):
                    message_id = result.get('message_id')

                    pin_start = time.perf_counter()
                    pin_result = await executor.bot.pin_chat_message(
                        chat_id=str(chat_id), message_id=message_id
                        )
                    pin_end = time.perf_counter()

                    add_log('tg_pin_message', 'Закреплено сообщение', 
                            duration_ms=(pin_end - pin_start) * 1000, 
                            pin_result=pin_result)

            overall_end = time.perf_counter()
            total_ms = int((overall_end - overall_start) * 1000)
            add_log('complete', f"Время выполнения {total_ms} ms", duration_ms=total_ms)

            return {"success": True, 
                    "message_id": result.get('message_id') or result.get('post_id'), 
                    "logs": action_log}
        else:
            error_msg = result.get('error') if result else 'Unknown error'
            add_log('send_failed', f"Не удалось отправить пост: {error_msg}", level='error')
            overall_end = time.perf_counter()
            total_ms = int((overall_end - overall_start) * 1000)
            add_log('complete', f"Время выполнения {total_ms} ms", duration_ms=total_ms)

            return {"success": False, "error": error_msg, "logs": action_log}

    except Exception as e:
        add_log('exception', f"Исключение: {e}", level='error')
        overall_end = time.perf_counter()
        total_ms = int((overall_end - overall_start) * 1000)
        add_log('complete', f"Время выполнения {total_ms} ms", duration_ms=total_ms)

        return {"success": False, "error": str(e), "logs": action_log}