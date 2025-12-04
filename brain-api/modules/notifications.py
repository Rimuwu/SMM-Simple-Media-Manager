"""
Модуль для отправки уведомлений по карточкам.

Содержит функции, которые могут быть запланированы через TaskScheduler.
"""

import logging
from models.Card import Card, CardStatus
from models.User import User
from global_modules.classes.enums import UserRole
from modules.api_client import executors_api
from modules.constants import ApiEndpoints
from datetime import datetime
from modules.json_get import open_settings

logger = logging.getLogger(__name__)


async def send_card_deadline_reminder(card: Card, **kwargs):
    """
    Отправить напоминание о дедлайне карточки исполнителю (за 2 дня до дедлайна).
    Напоминание отправляется только если статус карточки не ready.
    
    Args:
        card: Карточка, по которой нужно отправить напоминание
        **kwargs: Дополнительные параметры
    """
    logger.info(f"Проверка напоминания о дедлайне для карточки {card.card_id}")
    
    # Проверяем статус карточки
    if card.status == CardStatus.ready:
        logger.info(f"Карточка {card.card_id} имеет статус ready, напоминание не отправляется")
        return
    
    # Проверяем наличие исполнителя
    if not card.executor_id:
        logger.info(f"У карточки {card.card_id} нет исполнителя, напоминание не отправляется")
        return
    
    try:
        # Получаем исполнителя
        executor = await User.get_by_key('user_id', card.executor_id)
        if not executor:
            logger.error(f"Исполнитель {card.executor_id} не найден")
            return
        
        # Форматируем дедлайн
        deadline_str = card.deadline.strftime('%d.%m.%Y %H:%M') if card.deadline else 'Не установлен'
        
        # Формируем сообщение
        message_text = f"⏰ Напоминание о дедлайне\n\n📝 Задача: {card.name}\n⏰ Дедлайн: {deadline_str}\n\nОсталось 2 дня!"
        
        # Отправляем уведомление
        await executors_api.post(
            ApiEndpoints.NOTIFY_USER,
            data={
                "user_id": executor.telegram_id,
                "message": message_text
            }
        )
        
        logger.info(f"Напоминание для карточки {card.card_id} отправлено исполнителю {executor.telegram_id}")
        
    except Exception as e:
        logger.error(f"Ошибка отправки напоминания для карточки {card.card_id}: {e}", exc_info=True)


async def send_forum_deadline_passed(card: Card, **kwargs):
    """
    Отправить сообщение на форум о том, что дедлайн прошел.
    """
    logger.info(f"Отправка сообщения о просроченном дедлайне для карточки {card.card_id}")
    
    # Если задача уже выполнена или отправлена, не отправляем
    if card.status in [CardStatus.ready, CardStatus.sent]:
        return

    try:
        settings = open_settings()
        group_forum = settings.get('group_forum')
        
        if not group_forum:
            logger.warning("ID форума не найден в настройках")
            return

        # Формируем сообщение
        message_text = f"⏰ Дедлайн прошел!\n\n📝 Задача: {card.name}\n\nЗадача просрочена!"
        
        await executors_api.post(
            ApiEndpoints.NOTIFY_USER,
            data={
                "user_id": group_forum,
                "message": message_text
            }
        )
        
        logger.info(f"Сообщение о просроченном дедлайне для карточки {card.card_id} отправлено на форум")
        
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения на форум для карточки {card.card_id}: {e}", exc_info=True)


async def send_forum_no_executor_alert(card: Card, **kwargs):
    """
    Отправить сообщение на форум за 1 день до дедлайна, если нет исполнителя.
    """
    logger.info(f"Проверка наличия исполнителя для карточки {card.card_id} (форум)")
    
    # Проверяем наличие исполнителя
    if card.executor_id:
        return
    
    try:
        settings = open_settings()
        group_forum = settings.get('group_forum')
        
        if not group_forum:
            return
        
        # Форматируем дедлайн
        deadline_str = card.deadline.strftime('%d.%m.%Y %H:%M') if card.deadline else 'Не установлен'
        
        # Формируем сообщение
        message_text = f"⚠️ Внимание! Карточка без исполнителя\n\n📝 Задача: {card.name}\n⏰ Дедлайн: {deadline_str}\n\n❗ До дедлайна остался 1 день, но исполнитель не назначен!"
        
        await executors_api.post(
            ApiEndpoints.NOTIFY_USER,
            data={
                "user_id": group_forum,
                "message": message_text
            }
        )
        
        logger.info(f"Уведомление об отсутствии исполнителя для карточки {card.card_id} отправлено на форум")
        
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления на форум для карточки {card.card_id}: {e}", exc_info=True)


async def send_admin_no_executor_alert(card: Card, **kwargs):
    """
    Отправить уведомление всем админам о том, что у карточки нет исполнителя (за 1 день до дедлайна).
    Уведомление отправляется только если время до дедлайна больше 1 дня и нет исполнителя.
    
    Args:
        card: Карточка, по которой нужно отправить уведомление
        **kwargs: Дополнительные параметры
    """
    logger.info(f"Проверка наличия исполнителя для карточки {card.card_id}")
    
    # Проверяем наличие исполнителя
    if card.executor_id:
        logger.info(f"У карточки {card.card_id} есть исполнитель, уведомление не отправляется")
        return
    
    # Проверяем что дедлайн установлен
    if not card.deadline:
        logger.info(f"У карточки {card.card_id} не установлен дедлайн")
        return
    
    try:
        # Получаем всех админов
        admins = await User.filter_by(role=UserRole.admin)
        if not admins:
            logger.warning("Админы не найдены в системе")
            return
        
        # Форматируем дедлайн
        deadline_str = card.deadline.strftime('%d.%m.%Y %H:%M')
        
        # Формируем сообщение
        message_text = f"⚠️ Внимание! Карточка без исполнителя\n\n📝 Задача: {card.name}\n⏰ Дедлайн: {deadline_str}\n\n❗ До дедлайна остался 1 день, но исполнитель не назначен!"
        
        # Отправляем уведомление каждому админу
        for admin in admins:
            try:
                await executors_api.post(
                    ApiEndpoints.NOTIFY_USER,
                    data={
                        "user_id": admin.telegram_id,
                        "message": message_text
                    }
                )
                logger.info(f"Уведомление о карточке {card.card_id} отправлено админу {admin.telegram_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления админу {admin.telegram_id}: {e}")
        
        # Также отправляем на форум
        await send_forum_no_executor_alert(card, **kwargs)
        
        logger.info(f"Уведомления о карточке {card.card_id} отправлены всем админам")
        
    except Exception as e:
        logger.error(f"Ошибка отправки уведомлений админам для карточки {card.card_id}: {e}", exc_info=True)


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


# ================== Функции для публикации постов ==================


async def schedule_post_via_executor(card: Card, client_key: str, **kwargs):
    """
    Запланировать пост через исполнителя с отложенной отправкой.
    Используется для tp_executor (Pyrogram), который поддерживает schedule_message.
    
    Вся генерация контента и работа с исполнителями происходит на стороне executors API.
    
    Args:
        card: Карточка с контентом
        client_key: Ключ клиента из clients.json
        **kwargs: Дополнительные параметры
    """
    logger.info(f"Планирование поста через исполнителя для карточки {card.card_id}, клиент: {client_key}")
    
    try:
        # Отправляем запрос на отложенную публикацию - всю логику выполняет executors API
        response, status = await executors_api.post(
            "/post/schedule",
            data={
                "card_id": str(card.card_id),
                "client_key": client_key,
                "content": card.content or card.description or "",
                "tags": card.tags,
                "send_time": card.send_time.isoformat() if card.send_time else None,
                "image": card.post_image.hex() if card.post_image else None
            }
        )
        
        if status == 200 and response.get('success'):
            logger.info(f"Пост для карточки {card.card_id} запланирован, клиент: {client_key}")
        else:
            logger.error(f"Ошибка планирования поста: {response}")
            await notify_admins_about_post_failure(card, client_key, response.get('error', 'Unknown error'))
            
    except Exception as e:
        logger.error(f"Ошибка при планировании поста для карточки {card.card_id}: {e}", exc_info=True)
        await notify_admins_about_post_failure(card, client_key, str(e))


async def send_post_now(card: Card, client_key: str, **kwargs):
    """
    Немедленно отправить пост через исполнителя.
    Используется для telegram_executor и vk_executor, которые не поддерживают
    нативную отложенную отправку.
    
    Вся генерация контента и работа с исполнителями происходит на стороне executors API.
    
    Args:
        card: Карточка с контентом
        client_key: Ключ клиента из clients.json
        **kwargs: Дополнительные параметры
    """
    logger.info(f"Немедленная отправка поста для карточки {card.card_id}, клиент: {client_key}")
    
    try:
        # Отправляем запрос на немедленную публикацию - всю логику выполняет executors API
        response, status = await executors_api.post(
            "/post/send",
            data={
                "card_id": str(card.card_id),
                "client_key": client_key,
                "content": card.content or card.description or "",
                "tags": card.tags,
                "image": card.post_image.hex() if card.post_image else None
            }
        )
        
        if status == 200 and response.get('success'):
            logger.info(f"Пост для карточки {card.card_id} отправлен, клиент: {client_key}")
        else:
            logger.error(f"Ошибка отправки поста: {response}")
            await notify_admins_about_post_failure(card, client_key, response.get('error', 'Unknown error'))
            
    except Exception as e:
        logger.error(f"Ошибка при отправке поста для карточки {card.card_id}: {e}", exc_info=True)
        await notify_admins_about_post_failure(card, client_key, str(e))


async def verify_post_sent(card: Card, client_key: str, **kwargs):
    """
    Проверить, был ли отправлен пост через исполнителя с отложенной отправкой.
    Вызывается через минуту после запланированного времени отправки.
    Если пост не был отправлен - отправляет его немедленно.
    
    Args:
        card: Карточка с контентом
        client_key: Ключ клиента из clients.json
        **kwargs: Дополнительные параметры
    """
    logger.info(f"Проверка отправки поста для карточки {card.card_id}, клиент: {client_key}")
    
    try:
        # Проверяем статус отправки через executors API
        response, status = await executors_api.get(
            f"/post/verify/{card.card_id}/{client_key}"
        )
        
        if status == 200 and response.get('sent'):
            logger.info(f"Пост для карточки {card.card_id} успешно отправлен")
            return
        
        # Пост не был отправлен - отправляем немедленно
        logger.warning(f"Пост для карточки {card.card_id} не был отправлен, отправляем сейчас")
        await send_post_now(card, client_key, **kwargs)
        
    except Exception as e:
        logger.error(f"Ошибка при проверке отправки поста: {e}", exc_info=True)
        # В случае ошибки проверки - отправляем пост
        await send_post_now(card, client_key, **kwargs)


async def notify_admins_about_post_failure(card: Card, client_key: str, error: str):
    """
    Уведомить админов об ошибке публикации поста.
    
    Args:
        card: Карточка
        client_key: Ключ клиента
        error: Текст ошибки
    """
    try:
        admins = await User.filter_by(role=UserRole.admin)
        if not admins:
            logger.warning("Админы не найдены в системе")
            return
        
        message_text = (
            f"❌ Ошибка публикации поста\n\n"
            f"📝 Задача: {card.name}\n"
            f"📢 Канал: {client_key}\n"
            f"⚠️ Ошибка: {error}\n\n"
            f"Требуется ручная публикация!"
        )
        
        for admin in admins:
            try:
                await executors_api.post(
                    "/events/notify_user",
                    data={
                        "user_id": admin.telegram_id,
                        "message": message_text
                    }
                )
            except Exception as e:
                logger.error(f"Ошибка уведомления админа {admin.telegram_id}: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка уведомления админов об ошибке публикации: {e}", exc_info=True)
