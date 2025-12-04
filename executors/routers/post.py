"""
Роутер для управления публикацией постов через различных исполнителей.
Вся логика работы с исполнителями и генерацией контента находится здесь.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import aiohttp
from modules.executors_manager import manager
from modules.constants import CLIENTS
from modules.logs import executors_logger as logger
from modules.post_generator import generate_post
from modules.api_client import brain_api
from global_modules.timezone import now_naive as moscow_now

router = APIRouter(prefix="/post", tags=["Post"])

# Хранилище для отслеживания запланированных постов
# Формат: {card_id: {client_key: {"scheduled": bool, "sent": bool, "message_id": int}}}
scheduled_posts: dict = {}


async def download_kaiten_files(task_id: int, file_names: list[str]) -> list[bytes]:
    """
    Скачать файлы из Kaiten по именам.
    
    Args:
        task_id: ID карточки в Kaiten
        file_names: Список имён файлов для скачивания
    
    Returns:
        Список байтовых данных файлов
    """
    if not task_id or not file_names:
        return []
    
    downloaded_files = []
    
    try:
        # Получаем список файлов карточки
        response, status = await brain_api.get(f"/kaiten/get-files/{task_id}")
        
        if status != 200 or not response.get('files'):
            logger.warning(f"No files found for task {task_id}")
            return []
        
        kaiten_files = response['files']
        
        # Ищем файлы по именам и скачиваем
        for file_name in file_names:
            target_file = next(
                (f for f in kaiten_files if f.get('name') == file_name),
                None
            )
            
            if not target_file:
                logger.warning(f"File '{file_name}' not found in task {task_id}")
                continue
            
            file_id = target_file.get('id')
            if not file_id:
                continue
            
            # Скачиваем файл
            file_data, dl_status = await brain_api.get(
                f"/kaiten/files/{file_id}",
                params={"task_id": task_id},
                return_bytes=True
            )
            
            if dl_status == 200 and isinstance(file_data, bytes):
                downloaded_files.append(file_data)
                logger.info(f"Downloaded file '{file_name}' ({len(file_data)} bytes)")
            else:
                logger.error(f"Failed to download file '{file_name}'")
    
    except Exception as e:
        logger.error(f"Error downloading files from Kaiten: {e}", exc_info=True)
    
    return downloaded_files

class PostScheduleRequest(BaseModel):
    """Запрос на планирование поста"""
    card_id: str
    client_key: str
    content: str  # Сырой контент
    tags: Optional[list[str]] = None
    send_time: Optional[str] = None  # ISO 8601 format
    image: Optional[str] = None  # Hex-encoded binary data (устарело, для совместимости)
    post_images: Optional[list[dict]] = None  # Список фото с file_id из Telegram


class PostSendRequest(BaseModel):
    """Запрос на немедленную отправку поста"""
    card_id: str
    client_key: str
    content: str  # Сырой контент
    tags: Optional[list[str]] = None
    task_id: Optional[int] = None  # ID карточки в Kaiten для скачивания файлов
    post_images: Optional[list[str]] = None  # Список имён файлов из Kaiten


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


def get_platform_from_client_key(client_key: str) -> str:
    """Определить платформу по ключу клиента"""
    if "vk" in client_key.lower():
        return "vk"
    return "telegram"


@router.post("/schedule")
async def schedule_post(request: PostScheduleRequest):
    """
    Запланировать пост для исполнителя с поддержкой отложенной отправки.
    Используется для tp_executor (Pyrogram) который поддерживает schedule_message.
    
    Генерация контента происходит здесь, на стороне executors.
    """
    logger.info(f"Scheduling post for card {request.card_id}, client {request.client_key}")
    
    # Получаем конфигурацию клиента
    client_config, executor_name, client_id = get_client_config(request.client_key)
    
    # Получаем исполнителя
    executor = manager.get(executor_name)
    if not executor:
        logger.error(f"Executor {executor_name} not found or not available")
        return {"success": False, "error": f"Executor {executor_name} not found"}
    
    # Проверяем поддержку schedule_message
    if not hasattr(executor, 'schedule_message'):
        logger.error(f"Executor {executor_name} does not support schedule_message")
        return {"success": False, "error": "Executor does not support scheduled messages"}
    
    try:
        # Преобразуем время отправки
        send_time = None
        if request.send_time:
            send_time = datetime.fromisoformat(request.send_time)
        
        if not send_time:
            logger.error("send_time is required for scheduling")
            return {"success": False, "error": "send_time is required"}
        
        # Генерируем текст поста
        platform = get_platform_from_client_key(request.client_key)
        post_text = generate_post(
            content=request.content,
            tags=request.tags,
            platform=platform,
            client_key=request.client_key
        )
        
        # Преобразуем client_id
        try:
            chat_id = int(client_id)
        except ValueError:
            chat_id = client_id
        
        # Отправляем запланированное сообщение
        result = await executor.schedule_message(
            chat_id=chat_id,
            text=post_text,
            schedule_date=send_time
        )
        
        if result.get('success'):
            # Сохраняем информацию о запланированном посте
            if request.card_id not in scheduled_posts:
                scheduled_posts[request.card_id] = {}
            
            scheduled_posts[request.card_id][request.client_key] = {
                "scheduled": True,
                "sent": False,
                "schedule_time": send_time.isoformat(),
                "executor_name": executor_name,
                "client_id": chat_id
            }
            
            logger.info(f"Post scheduled successfully for card {request.card_id}, client {request.client_key}")
            return {"success": True, "scheduled_time": send_time.isoformat()}
        else:
            logger.error(f"Failed to schedule post: {result.get('error')}")
            return {"success": False, "error": result.get('error')}
            
    except Exception as e:
        logger.error(f"Error scheduling post: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.post("/send")
async def send_post(request: PostSendRequest):
    """
    Немедленно отправить пост.
    Используется для telegram_executor и vk_executor.
    
    Генерация контента происходит здесь, на стороне executors.
    Поддерживает отправку нескольких фото (media group).
    """
    logger.info(f"Sending post for card {request.card_id}, client {request.client_key}")
    
    # Получаем конфигурацию клиента
    client_config, executor_name, client_id = get_client_config(request.client_key)
    
    # Получаем исполнителя
    executor = manager.get(executor_name)
    if not executor:
        logger.error(f"Executor {executor_name} not found or not available")
        return {"success": False, "error": f"Executor {executor_name} not found"}
    
    try:
        # Генерируем текст поста
        platform = get_platform_from_client_key(request.client_key)
        post_text = generate_post(
            content=request.content,
            tags=request.tags,
            platform=platform,
            client_key=request.client_key
        )
        
        # Преобразуем client_id
        try:
            chat_id = int(client_id)
        except ValueError:
            chat_id = client_id
        
        # Определяем тип исполнителя и вызываем соответствующий метод
        executor_type = executor.get_type()
        result = None
        
        # Получаем имена файлов для отправки
        post_image_names = request.post_images or []
        
        # Скачиваем файлы из Kaiten если есть
        downloaded_images = []
        if post_image_names and request.task_id:
            downloaded_images = await download_kaiten_files(request.task_id, post_image_names)
            logger.info(f"Downloaded {len(downloaded_images)} images from Kaiten for card {request.card_id}")
        
        if executor_type == "vk":
            # Для VK используем create_wall_post
            result = await executor.create_wall_post(
                text=post_text
            )
        elif executor_type == "telegram":
            # Для Telegram - проверяем наличие фото
            if downloaded_images:
                # Отправляем с фото (bytes данные)
                if len(downloaded_images) == 1:
                    # Одно фото - send_photo
                    result = await executor.send_photo(
                        chat_id=chat_id,
                        photo=downloaded_images[0],  # bytes
                        caption=post_text
                    )
                else:
                    # Несколько фото - media group
                    result = await executor.send_media_group(
                        chat_id=chat_id,
                        media=downloaded_images,  # list[bytes]
                        caption=post_text
                    )
            else:
                # Без фото - просто текст
                result = await executor.send_message(
                    chat_id=chat_id,
                    text=post_text
                )
        else:
            # Для других исполнителей - просто текст
            result = await executor.send_message(
                chat_id=chat_id,
                text=post_text
            )
        
        if result and result.get('success'):
            # Сохраняем информацию об отправленном посте
            if request.card_id not in scheduled_posts:
                scheduled_posts[request.card_id] = {}
            
            scheduled_posts[request.card_id][request.client_key] = {
                "scheduled": False,
                "sent": True,
                "sent_at": moscow_now().isoformat(),
                "message_id": result.get('message_id') or result.get('post_id'),
                "executor_name": executor_name,
                "images_count": len(downloaded_images)
            }
            
            logger.info(f"Post sent successfully for card {request.card_id}, client {request.client_key}, images: {len(downloaded_images)}")
            return {
                "success": True, 
                "message_id": result.get('message_id') or result.get('post_id')
            }
        else:
            error_msg = result.get('error') if result else 'Unknown error'
            logger.error(f"Failed to send post: {error_msg}")
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        logger.error(f"Error sending post: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.get("/verify/{card_id}/{client_key}")
async def verify_post_sent(card_id: str, client_key: str):
    """
    Проверить, был ли отправлен пост.
    Вызывается через минуту после запланированного времени отправки.
    """
    logger.info(f"Verifying post for card {card_id}, client {client_key}")
    
    # Проверяем локальное хранилище
    card_posts = scheduled_posts.get(card_id, {})
    client_post = card_posts.get(client_key, {})
    
    if client_post.get('sent'):
        logger.info(f"Post for card {card_id}, client {client_key} was already sent")
        return {"sent": True, "message_id": client_post.get('message_id')}
    
    if not client_post.get('scheduled'):
        logger.warning(f"No scheduled post found for card {card_id}, client {client_key}")
        return {"sent": False, "error": "No scheduled post found"}
    
    # Если пост был запланирован, но статус sent не установлен,
    # считаем что пост отправлен (Telegram сам отправляет в нужное время)
    # Но проверить это сложно без получения истории сообщений
    
    # Для tp_executor - пост должен быть уже отправлен автоматически
    schedule_time_str = client_post.get('schedule_time')
    if schedule_time_str:
        schedule_time = datetime.fromisoformat(schedule_time_str)
        now = moscow_now()
        
        if now > schedule_time:
            # Время отправки прошло - считаем что пост отправлен
            # (Telegram должен был отправить автоматически)
            scheduled_posts[card_id][client_key]['sent'] = True
            logger.info(f"Post for card {card_id}, client {client_key} should have been sent by Telegram")
            return {"sent": True, "auto_sent": True}
    
    logger.warning(f"Post for card {card_id}, client {client_key} might not have been sent")
    return {"sent": False, "error": "Post was scheduled but may not have been sent"}


@router.get("/status/{card_id}")
async def get_post_status(card_id: str):
    """
    Получить статус публикации для всех клиентов карточки.
    """
    card_posts = scheduled_posts.get(card_id, {})
    
    if not card_posts:
        return {"card_id": card_id, "posts": {}, "message": "No posts found for this card"}
    
    return {"card_id": card_id, "posts": card_posts}


@router.delete("/cancel/{card_id}")
async def cancel_scheduled_posts(card_id: str, client_key: Optional[str] = None):
    """
    Отменить запланированные посты для карточки.
    Если указан client_key - отменяет только для конкретного клиента.
    
    Примечание: Отмена запланированного сообщения в Telegram требует удаления сообщения,
    что невозможно до его отправки. Эта функция просто удаляет запись из локального хранилища.
    """
    logger.info(f"Cancelling scheduled posts for card {card_id}, client {client_key}")
    
    if card_id not in scheduled_posts:
        return {"success": True, "message": "No posts to cancel"}
    
    if client_key:
        if client_key in scheduled_posts[card_id]:
            del scheduled_posts[card_id][client_key]
            logger.info(f"Cancelled post for client {client_key}")
    else:
        del scheduled_posts[card_id]
        logger.info(f"Cancelled all posts for card {card_id}")
    
    return {"success": True}
