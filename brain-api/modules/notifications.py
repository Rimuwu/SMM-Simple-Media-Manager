"""
Модуль для отправки уведомлений по карточкам.

Содержит функции, которые могут быть запланированы через TaskScheduler.
"""

import logging
from models.Card import Card

logger = logging.getLogger(__name__)


async def send_card_deadline_reminder(card: Card, **kwargs):
    """
    Отправить напоминание о дедлайне карточки.
    
    Args:
        card: Карточка, по которой нужно отправить напоминание
        **kwargs: Дополнительные параметры
    """
    logger.info(f"Отправка напоминания о дедлайне для карточки {card.card_id}")
    
    # TODO: Здесь логика отправки сообщения в Telegram/форум
    # Например:
    # message = f"Напоминание: дедлайн карточки '{card.name}' истекает {card.deadline}"
    # await bot.send_message(chat_id=..., text=message)
    
    logger.info(f"Напоминание для карточки {card.card_id} отправлено")


async def send_card_notification(card: Card, message_type: str = "default", **kwargs):
    """
    Отправить уведомление по карточке.
    
    Args:
        card: Карточка
        message_type: Тип сообщения (напоминание, уведомление и т.д.)
        **kwargs: Дополнительные параметры
    """
    logger.info(f"Отправка уведомления типа '{message_type}' для карточки {card.card_id}")
    
    # TODO: Логика отправки в зависимости от типа
    # if message_type == "deadline":
    #     await send_deadline_message(card)
    # elif message_type == "status_change":
    #     await send_status_change_message(card)
    
    logger.info(f"Уведомление для карточки {card.card_id} отправлено")


async def publish_card_content(card: Card, **kwargs):
    """
    Опубликовать контент карточки в запланированное время.
    
    Args:
        card: Карточка с контентом для публикации
        **kwargs: Дополнительные параметры
    """
    logger.info(f"Публикация контента карточки {card.card_id}")
    
    # TODO: Логика публикации контента
    # - Отправка в социальные сети
    # - Создание постов
    # - Обновление статуса карточки
    
    logger.info(f"Контент карточки {card.card_id} опубликован")


async def check_card_approval(card: Card, **kwargs):
    """
    Проверить статус согласования карточки.
    
    Args:
        card: Карточка для проверки
        **kwargs: Дополнительные параметры
    """
    logger.info(f"Проверка согласования карточки {card.card_id}")
    
    if card.need_check:
        # TODO: Отправить напоминание о необходимости проверки
        logger.info(f"Карточка {card.card_id} ожидает проверки")
    
    logger.info(f"Проверка карточки {card.card_id} завершена")
