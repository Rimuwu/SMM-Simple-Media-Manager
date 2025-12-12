"""
Роутер для управления публикацией постов через различных исполнителей.
Вся логика работы с исполнителями и генерацией контента находится здесь.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from modules.executors_manager import manager
from modules.constants import CLIENTS
from modules.logs import executors_logger as logger
from modules.post_generator import generate_post
from modules.post_sender import download_kaiten_files

router = APIRouter(prefix="/post", tags=["Post"])

class PostScheduleRequest(BaseModel):
    """Запрос на планирование поста"""
    card_id: str
    client_key: str
    content: str  # Сырой контент
    tags: Optional[list[str]] = None
    send_time: Optional[str] = None  # ISO 8601 format
    task_id: Optional[int] = None  # ID карточки в Kaiten для скачивания файлов
    post_images: Optional[list[str]] = None  # Список имён файлов из Kaiten


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
        post_text = generate_post(
            content=request.content,
            tags=request.tags,
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
        downloaded_files = []
        if post_image_names and request.task_id:
            downloaded_files = await download_kaiten_files(request.task_id, post_image_names)
            logger.info(f"Downloaded {len(downloaded_files)} files from Kaiten for card {request.card_id}")

        if executor_type == "vk":
            executor: "VkExecutor" = executor  # type: ignore

            # Для VK - загружаем фото/видео и создаём пост
            attachments = []
            if downloaded_files:
                logger.info(f"VK: Начинаю загрузку {len(downloaded_files)} файлов для поста")

                import tempfile
                import os as os_module

                for idx, file_info in enumerate(downloaded_files):
                    file_data = file_info['data']
                    file_type = file_info['type']
                    file_name = file_info['name']
                    
                    logger.info(
                        f"VK: Обработка файла {idx + 1}/{len(downloaded_files)}, "
                        f"тип: {file_type}, размер: {len(file_data)} bytes")

                    # Сохраняем во временный файл для загрузки
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_name}") as tmp_file:
                        tmp_file.write(file_data)
                        tmp_path = tmp_file.name

                    logger.info(f"VK: Сохранено во временный файл: {tmp_path}")

                    try:
                        if file_type == 'photo':
                            upload_result = await executor.upload_photo_to_wall(tmp_path)
                            logger.info(f"VK: Результат загрузки фото: {upload_result}")
                        elif file_type == 'video':
                            upload_result = await executor.upload_video_to_wall(tmp_path)
                            logger.info(f"VK: Результат загрузки видео: {upload_result}")
                        else:
                            logger.warning(f"VK: Неподдерживаемый тип файла: {file_type}, пропускаю")
                            continue

                        if upload_result.get('success') and upload_result.get('attachment'):
                            attachments.append(upload_result['attachment'])
                            logger.info(f"VK: Attachment добавлен: {upload_result['attachment']}")
                        else:
                            logger.error(f"VK: Ошибка загрузки {file_type}: {upload_result.get('error')}")

                    finally:
                        os_module.unlink(tmp_path)
                        logger.info(f"VK: Временный файл удалён: {tmp_path}")

                logger.info(f"VK: Всего attachments для поста: {attachments}")

            result = await executor.create_wall_post(
                text=post_text,
                attachments=attachments if attachments else None
            )

        elif executor_type == "telegram":
            executor: "TelegramExecutor" = executor  # type: ignore

            # Для Telegram - проверяем наличие медиа файлов
            if downloaded_files:
                # Разделяем на фото и видео
                # photos = [f for f in downloaded_files if f['type'] == 'photo']
                # videos = [f for f in downloaded_files if f['type'] == 'video']
                
                if len(downloaded_files) == 1:
                    # Одиночный файл
                    file_info = downloaded_files[0]
                    if file_info['type'] == 'photo':
                        result = await executor.send_photo(
                            chat_id=chat_id,
                            photo=file_info['data'],
                            caption=post_text
                        )
                    elif file_info['type'] == 'video':
                        result = await executor.send_video(
                            chat_id=chat_id,
                            video=file_info['data'],
                            caption=post_text
                        )
                    else:
                        # Неизвестный тип - отправляем как документ
                        result = await executor.send_document(
                            chat_id=chat_id,
                            document=file_info['data'],
                            caption=post_text
                        )
                else:
                    # Несколько файлов - media group
                    result = await executor.send_media_group(
                        chat_id=chat_id,
                        media=downloaded_files,  # list[dict] с type и data
                        caption=post_text
                    )
            else:
                # Без медиа - просто текст
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
            logger.info(
                f"Post sent successfully for card {request.card_id}, client {request.client_key}, files: {len(downloaded_files)}")
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