
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from modules.logs import calendar_logger

from global_modules.vault.vault_client import vault_getenv

class GoogleCalendarManager:
    """Менеджер для работы с Google Calendar API"""

    def __init__(self):
        self.service = None
        self.calendar_id = None
        self._initialize_service()

    def _initialize_service(self):
        """Инициализация сервиса Google Calendar"""
        try:
            # Получение данных из переменных окружения
            service_account_info = vault_getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            self.calendar_id = vault_getenv('GOOGLE_CALENDAR_ID')

            if not service_account_info:
                raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON environment variable is not set")

            if not self.calendar_id:
                raise ValueError("GOOGLE_CALENDAR_ID environment variable is not set")

            # Парсинг JSON из переменной окружения
            try:
                service_account_data = json.loads(service_account_info)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {e}")

            # Создание credentials
            credentials = service_account.Credentials.from_service_account_info(
                service_account_data,
                scopes=['https://www.googleapis.com/auth/calendar']
            )

            # Создание сервиса
            self.service = build('calendar', 'v3', credentials=credentials)
            calendar_logger.info("Google Calendar service initialized successfully")

        except Exception as e:
            calendar_logger.error(f"Failed to initialize Google Calendar service: {e}")
            raise

    def create_event(self, 
                    title: str,
                    description: str = "",
                    start_time: datetime = None,
                    end_time: datetime = None,
                    all_day: bool = False,
                    attendees: List[str] = None,
                    location: str = "",
                    color_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Создание события в календаре

        Args:
            title: Название события
            description: Описание события
            start_time: Время начала события
            end_time: Время окончания события
            all_day: Событие на весь день
            attendees: Список email участников
            location: Место проведения
            color_id: ID цвета события (1-11, см. Google Calendar API)
                "1" - Лавандовый
                "2" - Зеленый мудрец
                "3" - Виноградный
                "4" - Фламинго
                "5" - Банановый
                "6" - Мандариновый
                "7" - Павлиний
                "8" - Графитовый
                "9" - Черничный
                "10" - Базиликовый
                "11" - Томатный

        Returns:
            Словарь с данными созданного события или None при ошибке
        """
        try:
            if not self.service:
                calendar_logger.error("Calendar service not initialized")
                return None

            # Подготовка времени
            if all_day:
                if not start_time:
                    start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                if not end_time:
                    end_time = start_time + timedelta(days=1)

                # Убираем timezone info для событий на весь день
                if start_time.tzinfo is not None:
                    start_time = start_time.replace(tzinfo=None)
                if end_time.tzinfo is not None:
                    end_time = end_time.replace(tzinfo=None)

                event_start = {'date': start_time.strftime('%Y-%m-%d')}
                event_end = {'date': end_time.strftime('%Y-%m-%d')}
            else:
                if not start_time:
                    start_time = datetime.now()
                if not end_time:
                    end_time = start_time + timedelta(hours=1)

                # Убираем timezone info и добавляем UTC
                if start_time.tzinfo is not None:
                    start_time = start_time.replace(tzinfo=None)
                if end_time.tzinfo is not None:
                    end_time = end_time.replace(tzinfo=None)

                event_start = {'dateTime': start_time.isoformat() + 'Z', 'timeZone': 'UTC'}
                event_end = {'dateTime': end_time.isoformat() + 'Z', 'timeZone': 'UTC'}

            # Подготовка участников
            event_attendees = []
            if attendees:
                event_attendees = [{'email': email} for email in attendees]

            # Создание события
            event = {
                'summary': title,
                'description': description,
                'location': location,
                'start': event_start,
                'end': event_end,
                'attendees': event_attendees,
            }

            # Добавляем цвет события, если указан
            if color_id:
                event['colorId'] = str(color_id)

            # Отправка запроса
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()

            calendar_logger.info(f"Event created successfully: {created_event.get('id')}")
            return created_event

        except HttpError as e:
            calendar_logger.error(f"HTTP error while creating event: {e}")
            return None
        except Exception as e:
            calendar_logger.error(f"Error while creating event: {e}")
            return None

    def get_events(self,
                   time_min: datetime = None,
                   time_max: datetime = None,
                   max_results: int = 10,
                   single_events: bool = True,
                   order_by: str = 'startTime') -> List[Dict[str, Any]]:
        """
        Получение списка событий из календаря

        Args:
            time_min: Минимальное время для поиска событий
            time_max: Максимальное время для поиска событий
            max_results: Максимальное количество результатов
            single_events: Развернуть повторяющиеся события
            order_by: Сортировка результатов

        Returns:
            Список событий
        """
        try:
            if not self.service:
                calendar_logger.error("Calendar service not initialized")
                return []

            # Подготовка временных рамок
            if not time_min:
                time_min = datetime.now()
            if not time_max:
                time_max = time_min + timedelta(days=30)

            # Убираем timezone info и форматируем для Google API
            if time_min.tzinfo is not None:
                time_min = time_min.replace(tzinfo=None)
            if time_max.tzinfo is not None:
                time_max = time_max.replace(tzinfo=None)

            # Запрос событий
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min.isoformat() + 'Z',
                timeMax=time_max.isoformat() + 'Z',
                maxResults=max_results,
                singleEvents=single_events,
                orderBy=order_by
            ).execute()

            events = events_result.get('items', [])
            calendar_logger.info(f"Retrieved {len(events)} events")
            return events
  
        except HttpError as e:
            calendar_logger.error(f"HTTP error while getting events: {e}")
            return []
        except Exception as e:
            calendar_logger.error(f"Error while getting events: {e}")
            return []

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение конкретного события по ID

        Args:
            event_id: ID события

        Returns:
            Данные события или None
        """
        try:
            if not self.service:
                calendar_logger.error("Calendar service not initialized")
                return None

            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            calendar_logger.info(f"Retrieved event: {event_id}")
            return event

        except HttpError as e:
            calendar_logger.error(f"HTTP error while getting event {event_id}: {e}")
            return None
        except Exception as e:
            calendar_logger.error(f"Error while getting event {event_id}: {e}")
            return None

    def update_event(self,
                    event_id: str,
                    title: str = None,
                    description: str = None,
                    start_time: datetime = None,
                    end_time: datetime = None,
                    location: str = None,
                    attendees: List[str] = None,
                    color_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Обновление существующего события

        Args:
            event_id: ID события для обновления
            title: Новое название события
            description: Новое описание события
            start_time: Новое время начала
            end_time: Новое время окончания
            location: Новое место проведения
            attendees: Новый список участников
            color_id: Новый ID цвета события (1-11, см. Google Calendar API)

        Returns:
            Обновленное событие или None
        """
        try:
            if not self.service:
                calendar_logger.error("Calendar service not initialized")
                return None

            # Получаем текущее событие
            current_event = self.get_event(event_id)
            if not current_event:
                return None

            # Определяем, является ли исходное событие all-day (использует 'date' вместо 'dateTime')
            is_all_day = 'date' in current_event.get('start', {})

            # Обновляем только переданные поля
            if title is not None:
                current_event['summary'] = title
            if description is not None:
                current_event['description'] = description
            if location is not None:
                current_event['location'] = location

            if start_time is not None:
                # Убираем timezone info если есть
                if start_time.tzinfo is not None:
                    start_time = start_time.replace(tzinfo=None)
                
                if is_all_day:
                    # Для all-day событий используем формат date
                    current_event['start'] = {'date': start_time.strftime('%Y-%m-%d')}
                else:
                    current_event['start'] = {
                        'dateTime': start_time.isoformat() + 'Z',
                        'timeZone': 'UTC'
                    }

            if end_time is not None:
                # Убираем timezone info если есть
                if end_time.tzinfo is not None:
                    end_time = end_time.replace(tzinfo=None)
                
                if is_all_day:
                    # Для all-day событий используем формат date
                    current_event['end'] = {'date': end_time.strftime('%Y-%m-%d')}
                else:
                    current_event['end'] = {
                        'dateTime': end_time.isoformat() + 'Z',
                        'timeZone': 'UTC'
                    }

            if attendees is not None:
                current_event['attendees'] = [{'email': email} for email in attendees]

            if color_id is not None:
                current_event['colorId'] = str(color_id)

            # Обновляем событие
            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=current_event
            ).execute()

            calendar_logger.info(f"Event updated successfully: {event_id}")
            return updated_event

        except HttpError as e:
            calendar_logger.error(f"HTTP error while updating event {event_id}: {e}")
            return None
        except Exception as e:
            calendar_logger.error(f"Error while updating event {event_id}: {e}")
            return None

    def delete_event(self, event_id: str) -> bool:
        """
        Удаление события

        Args:
            event_id: ID события для удаления

        Returns:
            True если удалено успешно, False при ошибке
        """
        try:
            if not self.service:
                calendar_logger.error("Calendar service not initialized")
                return False

            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            calendar_logger.info(f"Event deleted successfully: {event_id}")
            return True

        except HttpError as e:
            calendar_logger.error(f"HTTP error while deleting event {event_id}: {e}")
            return False
        except Exception as e:
            calendar_logger.error(f"Error while deleting event {event_id}: {e}")
            return False

    def get_calendar_info(self) -> Optional[Dict[str, Any]]:
        """
        Получение информации о календаре

        Returns:
            Информация о календаре или None
        """
        try:
            if not self.service:
                calendar_logger.error("Calendar service not initialized")
                return None

            calendar_info = self.service.calendars().get(
                calendarId=self.calendar_id
            ).execute()

            calendar_logger.info(f"Retrieved calendar info: {calendar_info.get('summary', 'Unknown')}")
            return calendar_info

        except HttpError as e:
            calendar_logger.error(f"HTTP error while getting calendar info: {e}")
            return None
        except Exception as e:
            calendar_logger.error(f"Error while getting calendar info: {e}")
            return None

    def check_availability(self,
                          start_time: datetime,
                          end_time: datetime) -> bool:
        """
        Проверка доступности времени в календаре

        Args:
            start_time: Время начала проверяемого периода
            end_time: Время окончания проверяемого периода

        Returns:
            True если время свободно, False если занято
        """
        try:
            events = self.get_events(
                time_min=start_time,
                time_max=end_time,
                max_results=100
            )

            for event in events:
                event_start = event.get('start', {})
                event_end = event.get('end', {})

                # Получаем время начала и окончания события
                if 'dateTime' in event_start:
                    event_start_time = datetime.fromisoformat(
                        event_start['dateTime'].replace('Z', '+00:00')
                    )
                elif 'date' in event_start:
                    event_start_time = datetime.fromisoformat(event_start['date'])
                else:
                    continue

                if 'dateTime' in event_end:
                    event_end_time = datetime.fromisoformat(
                        event_end['dateTime'].replace('Z', '+00:00')
                    )
                elif 'date' in event_end:
                    event_end_time = datetime.fromisoformat(event_end['date'])
                else:
                    continue

                # Проверяем пересечение времени
                if (start_time < event_end_time and end_time > event_start_time):
                    calendar_logger.info(f"Time conflict found with event: {event.get('summary', 'Unknown')}")
                    return False

            calendar_logger.info("Time slot is available")
            return True

        except Exception as e:
            calendar_logger.error(f"Error while checking availability: {e}")
            return False


# Создание глобального экземпляра менеджера
calendar_manager = GoogleCalendarManager()
