

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from modules.logs import executors_logger as logger
from modules.executors_manager import manager
from aiogram import F
from aiogram.filters import Command
from datetime import datetime, timedelta

from global_modules.api_client import APIClient

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp

api = APIClient('http://executors:8003')
calendar_api = APIClient('http://calendar:8001')

@dp.message(Command('send_to_me'))
async def send_to_me(message: Message):

    data = {
        'executor_name': 'telegram_executor',
        'chat_id': message.chat.id,
        'text': f'Hello, {message.from_user.full_name}! This is a test message from /send_to_me command.'
    }

    await api.post('/test/send-message', data=data)


@dp.message(Command('create_event'))
async def create_calendar_event(message: Message):
    """
    Команда для создания события в календаре на весь день завтра
    Использование: /create_event Название события
    """
    try:
        # Получаем текст команды и извлекаем название события
        command_text = message.text
        if not command_text or len(command_text.split(' ', 1)) < 2:
            await message.reply(
                "❌ Укажите название события!\n"
                "Пример: /create_event Важная встреча"
            )
            return
        
        # Извлекаем название события (все после команды)
        event_title = command_text.split(' ', 1)[1].strip()
        
        if not event_title:
            await message.reply("❌ Название события не может быть пустым!")
            return
        
        # Готовим дату на завтра (весь день)
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Данные для создания события
        event_data = {
            'title': event_title,
            'description': f'Событие создано пользователем {message.from_user.full_name} через Telegram бота',
            'start_time': tomorrow_start.isoformat() + 'Z',
            'all_day': True,
            'location': '',
            'attendees': []
        }
        
        logger.info(f"Creating calendar event: {event_title} for user {message.from_user.id}")
        
        # Отправляем запрос к Calendar API
        response_data, status_code = await calendar_api.post('/calendar/events', data=event_data)
        
        if status_code == 200 and response_data and response_data.get('success'):
            event_id = response_data.get('data', {}).get('id', 'unknown')
            await message.reply(
                f"✅ Событие успешно создано!\n\n"
                f"📅 Название: {event_title}\n"
                f"🗓 Дата: {tomorrow_start.strftime('%d.%m.%Y')} (весь день)\n"
                f"🆔 ID события: {event_id[:20]}..."
            )
            logger.info(f"Calendar event created successfully: {event_id}")
        else:
            error_detail = response_data.get('detail', 'Неизвестная ошибка') if response_data else f'HTTP {status_code}'
            await message.reply(
                f"❌ Ошибка при создании события!\n"
                f"Статус: {status_code}\n"
                f"Детали: {error_detail}"
            )
            logger.error(f"Failed to create calendar event: {status_code} - {error_detail}")
            
    except Exception as e:
        logger.error(f"Error in create_calendar_event handler: {e}")
        await message.reply(
            f"❌ Произошла ошибка при создании события!\n"
            f"Ошибка: {str(e)}"
        )


@dp.message(Command('events_tomorrow'))
async def get_tomorrow_events(message: Message):
    """
    Команда для просмотра событий на завтра
    Использование: /events_tomorrow
    """
    try:
        # Готовим даты для завтра
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_end = tomorrow_start + timedelta(days=1)
        
        logger.info(f"Getting tomorrow events for user {message.from_user.id}")
        
        # Запрашиваем события на завтра
        response_data, status_code = await calendar_api.get('/calendar/events', params={
            'time_min': tomorrow_start.isoformat() + 'Z',
            'time_max': tomorrow_end.isoformat() + 'Z',
            'max_results': 20
        })
        
        if status_code == 200 and response_data and response_data.get('success'):
            events = response_data.get('data', [])
            count = response_data.get('count', 0)
            
            if count == 0:
                await message.reply(
                    f"📅 События на {tomorrow_start.strftime('%d.%m.%Y')}\n\n"
                    "🚫 На завтра событий не запланировано"
                )
            else:
                # Формируем список событий
                events_text = f"📅 События на {tomorrow_start.strftime('%d.%m.%Y')} ({count} шт.)\n\n"
                
                for i, event in enumerate(events[:10], 1):  # Показываем максимум 10 событий
                    title = event.get('summary', 'Без названия')
                    start = event.get('start', {})
                    
                    # Определяем время события
                    if 'date' in start:
                        time_info = "весь день"
                    elif 'dateTime' in start:
                        try:
                            event_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                            time_info = event_time.strftime('%H:%M')
                        except:
                            time_info = "время не указано"
                    else:
                        time_info = "время не указано"
                    
                    location = event.get('location', '')
                    location_text = f" 📍 {location}" if location else ""
                    
                    events_text += f"{i}. 📝 {title}\n   ⏰ {time_info}{location_text}\n\n"
                
                if count > 10:
                    events_text += f"... и еще {count - 10} событий"
                
                await message.reply(events_text)
                
            logger.info(f"Successfully retrieved {count} tomorrow events")
        else:
            error_detail = response_data.get('detail', 'Неизвестная ошибка') if response_data else f'HTTP {status_code}'
            await message.reply(
                f"❌ Ошибка при получении событий!\n"
                f"Статус: {status_code}\n"
                f"Детали: {error_detail}"
            )
            logger.error(f"Failed to get tomorrow events: {status_code} - {error_detail}")
            
    except Exception as e:
        logger.error(f"Error in get_tomorrow_events handler: {e}")
        await message.reply(
            f"❌ Произошла ошибка при получении событий!\n"
            f"Ошибка: {str(e)}"
        )