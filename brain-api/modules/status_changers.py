import asyncio
from datetime import datetime, timedelta
from typing import Literal, Optional
from uuid import UUID as _UUID
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from database.connection import session_factory
from global_modules.classes.enums import CardType, ChangeType, UserRole
from global_modules.timezone import now_naive as moscow_now
from modules.kaiten import kaiten
from modules.properties import multi_properties
from global_modules.json_get import open_settings, open_properties
from models.Card import Card, CardStatus
from models.User import User
from modules.calendar import create_calendar_event, delete_calendar_event, update_calendar_event
from modules.scheduler import reschedule_post_tasks, schedule_card_notifications, cancel_card_tasks, reschedule_card_notifications, schedule_post_tasks
from modules.constants import (
    KaitenBoardNames, PropertyNames, 
    SceneNames, Messages
)
from modules.card_service import (
    notify_executor, get_kaiten_user_name, add_kaiten_comment, 
    update_kaiten_card_field, increment_reviewers_tasks, increment_customer_tasks
)
from modules.executors_client import (
    send_forum_message, update_forum_message, delete_forum_message, delete_forum_message_by_id,
    send_complete_preview, update_complete_preview, delete_complete_preview, delete_all_complete_previews,
    close_user_scene, update_task_scenes, close_card_related_scenes,
    notify_user, notify_users
)
from modules.logs import brain_logger as logger

settings = open_settings() or {}

BOARD_QUEUE_ID = settings['space']['boards'][KaitenBoardNames.QUEUE]['id']
COLUMN_QUEUE_FORUM_ID = settings['space']['boards'][KaitenBoardNames.QUEUE]['columns'][0]['id']

async def to_pass(
          card: Optional[Card] = None,
          card_id: Optional[_UUID] = None, 
          who_changed: Literal['executor', 'admin'] = 'admin'
                  ):
    """ Возвращение задачи в статус "Создано"
        Используется для возврата задачи 
        исполнителем / админом на форум задач
        или снятия задачи с исполнения админом

        Если есть исполнитель:
          Убрать исполнителя в базе и в кайтене +
          Закрыть сцену, если она открыта +

        Если админ изменил статус:
          Уведомление исполнителю +

        DOWNGRADE
        Если есть запланированные задачи:
          (статус: ready)
          Снять все запланированные задачи

        DOWNGRADE
        Если есть отправленные "готовые варианты":
          (статус: ready)
          Удалить все complete_messages +

        Написать комментарий в кайтене +
        Обновить колонку в кайтене +
        Обновить сцены просмотра задачи tasks +
        Новые задачи напоминания

        Если тип public:
         Переотправить сообщение на форуме

        Если тип private:
         Отправить уведомление заказчику
         Отправить уведомление админу
    """

    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")

    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")

    data_update: dict = {
        'status': CardStatus.pass_,
    }

    if card.executor_id:
        executor = await User.get_by_key('user_id', card.executor_id)
        if executor:

            if executor.tasker_id and card.task_id:
                async with kaiten as kc:
                    await kc.remove_card_member(
                        card_id=card.task_id,
                        user_id=executor.tasker_id
                    )

            if executor.telegram_id:
                if who_changed == 'admin':
                    await asyncio.create_task(
                        notify_user(
                            executor.telegram_id,
                            "🎇 Задание возвращено на форум задач администратором."
                        )
                    )

                await close_card_related_scenes(str(card.card_id))

            async with session_factory() as session:
                await cancel_card_tasks(
                    session=session,
                    card_id=str(card.card_id)
                )

                await schedule_card_notifications(
                    session=session,
                    card=card
                )

            if card.complete_message_id:
                await asyncio.create_task(
                    delete_complete_preview(
                        card.complete_message_id.get('post_id'),
                        card.complete_message_id.get('posts_id'),
                        card.complete_message_id.get('info_id')
                        )
                )

            async with kaiten as kc:
                await kc.add_comment(
                    card_id=card.task_id,
                    text="📤 Задача возвращена на форум задач."
                )

                await kc.update_card(
                    card.task_id,
                    executor_id=None,
                    board_id=BOARD_QUEUE_ID,
                    column_id=COLUMN_QUEUE_FORUM_ID
                )

            await update_task_scenes(
                card_id=str(card.card_id),
                scene_name=SceneNames.VIEW_TASK
            )

        data_update['executor_id'] = None



async def to_edited():
    """ 1. Взятие / назаначение задачи
        Копирайтер взял задачу в работу с форума
        Или админ назначил задачу исполнителю (при создании приватный тип / назначен админом как исполнитель)
        Или админ нажал "взять в работу" в задаче

        2. Задачу вернули на доработку
        Исполнитель / редактор вернул задачу на доработку исполнителю

        Написать комментарий в кайтене
        Обновить колонку в кайтене
        Обновить сцены просмотра задачи tasks
        Таски напоминаний

        Обновить сцену редактирования задачи
        Открыть сцену редактирования задачи исполнителю

        Если тип public:
         Обновить сообщение на форуме

        Если тип private и прошлый статус pass:
         Отправить уведомление заказчику

        DOWNGRADE
        Если есть запланированные задачи:
          (статус: ready)
          Снять все запланированные задачи

        DOWNGRADE
        Если есть отправленные "готовые варианты":
          (статус: ready)
          Удалить все complete_messages
    """
    pass

async def to_review():
    """ Отправка задания на редактирование 

        Написать комментарий в кайтене
        Обновить колонку в кайтене
        Обновить сцены просмотра задачи tasks
        Очистить таски отправки

        Обновить сцену редактирования задачи

        Если выбран редактор:
          Отправить уведомление редактору

        Если не выбран редактор:
          Переотправить сообщение на форум с кнопкой для редакторов "взять задание"

          Отправить уведомление редакторам

        DOWNGRADE
        Если есть запланированные задачи:
          (статус: ready)
          Снять все запланированные задачи

        DOWNGRADE
        Если есть отправленные "готовые варианты":
          (статус: ready)
          Удалить все complete_messages
    """
    pass

async def to_ready():
    """ Завершение работы над задачей

        Написать комментарий в кайтене
        Обновить колонку в кайтене
        Обновить сцены просмотра задачи tasks
        Обновить сцену редактирования задачи

        Закрыть сцену редактирования задачи всем

        Очищаем таски отправки и напоминаний
        Если need_send:
         Планируем задачи отправки

        Переотправка сообщения на форуме
        Отправляем / редактируем превью постов

        Уведомляем заказчика о готовности задачи (если завершил не сам заказчик)
        Удаляем сообщение дизайнерам

    """
    pass

async def to_sent():
    """ Задача отправлена в каналы

        Написать комментарий в кайтене
        Обновить сцены просмотра задачи tasks
        Обновить сцену редактирования задачи

        Удалить сообщение с форума

        Увеличить счетчик выполненных задач исполнителя
        Увеличить счетчик проверенных задач редактора

        Добавить задачу на удаление карточки из базы
    """
    pass