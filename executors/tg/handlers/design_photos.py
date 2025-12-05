"""
Обработчик ответов на сообщения дизайнерам с фотографиями
"""
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from modules.executors_manager import manager
from modules.api_client import brain_api
from modules.constants import SETTINGS
from modules.logs import executors_logger as logger

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp
bot: Bot = client_executor.bot


@dp.message(F.photo, F.reply_to_message)
async def handle_design_photo_reply(message: Message):
    """
    Обработчик фото-ответов на сообщения с ТЗ дизайнерам.
    Добавляет фото к задаче через Kaiten.
    """
    design_group = SETTINGS.get('design_group')
    
    # Проверяем, что сообщение из группы дизайнеров
    if message.chat.id != design_group:
        return
    
    # Получаем ID сообщения, на которое ответили
    reply_message_id = message.reply_to_message.message_id
    
    # Ищем карточку по prompt_message
    try:
        # Получаем все карточки и фильтруем по prompt_message
        response, status = await brain_api.get(
            '/card/get',
            params={}
        )
        
        if status != 200:
            return
        
        # Ищем карточку с нужным prompt_message
        card = None
        for c in response:
            if c.get('prompt_message') == reply_message_id:
                card = c
                break
        
        if not card:
            # Это не ответ на наше сообщение
            return
        
        logger.info(f"Получено фото для задачи {card['card_id']} от {message.from_user.id}")
        
        # Получаем файл фото (берём самое большое разрешение)
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        file_data = await bot.download_file(file.file_path)
        
        # Формируем имя файла
        file_name = f"design_{message.from_user.id}_{message.message_id}.jpg"
        
        # Загружаем файл в Kaiten через brain API
        card_id = card.get('card_id')
        
        try:
            # Используем multipart/form-data для загрузки файла
            form_data = aiohttp.FormData()
            form_data.add_field('card_id', str(card_id))
            form_data.add_field(
                'file',
                file_data.read(),
                filename=file_name,
                content_type='image/jpeg'
            )
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'http://brain:8000/kaiten/upload-file',
                    data=form_data
                ) as resp:
                    if resp.status == 200:
                        await message.reply(
                            "✅ Фото добавлено к задаче!",
                            parse_mode="Markdown"
                        )
                        logger.info(f"Фото {file_name} загружено для задачи {card_id}")
                    else:
                        error_text = await resp.text()
                        await message.reply(
                            "⚠️ Не удалось загрузить фото.",
                            parse_mode="Markdown"
                        )
                        logger.error(f"Ошибка загрузки фото: {error_text}")
                    
        except Exception as e:
            logger.error(f"Ошибка загрузки файла: {e}")
            await message.reply(
                f"⚠️ Ошибка при загрузке: {str(e)[:100]}",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Ошибка обработки фото-ответа: {e}")
