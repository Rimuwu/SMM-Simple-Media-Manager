import asyncio
from typing import Literal, Optional
from uuid import UUID as _UUID
from database.connection import session_factory
from global_modules.classes.enums import UserRole
from modules.kaiten import kaiten
from global_modules.json_get import open_settings
from models.Card import Card, CardStatus
from models.User import User
from modules.scheduler import schedule_card_notifications, cancel_card_tasks, schedule_post_tasks
from modules.constants import (
    KaitenBoardNames, 
    SceneNames, Messages
)
from modules.card_service import increment_reviewers_tasks
from modules.executors_client import (
    send_forum_message, update_forum_message, delete_forum_message, delete_forum_message_by_id,
    send_complete_preview, update_complete_preview, delete_complete_preview, delete_all_complete_previews,
    close_user_scene, update_task_scenes, close_card_related_scenes,
    notify_user, notify_users
)
from modules.logs import brain_logger as logger
from models.CardMessage import CardMessage

settings = open_settings() or {}

# Константы для Kaiten
BOARD_QUEUE_ID = settings['space']['boards'][KaitenBoardNames.QUEUE]['id']
COLUMN_QUEUE_FORUM_ID = settings['space']['boards'][KaitenBoardNames.QUEUE]['columns'][0]['id']

BOARD_IN_PROGRESS_ID = settings['space']['boards'][KaitenBoardNames.IN_PROGRESS]['id']
COLUMN_IN_PROGRESS_EDITED_ID = settings['space']['boards'][KaitenBoardNames.IN_PROGRESS]['columns'][0]['id']
COLUMN_IN_PROGRESS_REVIEW_ID = settings['space']['boards'][KaitenBoardNames.IN_PROGRESS]['columns'][1]['id']
COLUMN_IN_PROGRESS_READY_ID = settings['space']['boards'][KaitenBoardNames.IN_PROGRESS]['columns'][2]['id']

async def to_pass(
          card: Optional[Card] = None,
          card_id: Optional[_UUID] = None, 
          who_changed: Literal[
              'executor', 'admin'] = 'admin'
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
          Снять все запланированные задачи +

        DOWNGRADE
        Если есть отправленные "готовые варианты":
          (статус: ready)
          Удалить все complete_messages +

        Написать комментарий в кайтене +
        Обновить колонку в кайтене +
        Обновить сцены просмотра задачи tasks +
        Новые задачи напоминания +

        Если тип public:
         Переотправить сообщение на форуме +

        Если тип private:
         Отправить уведомление заказчику +
    """

    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")

    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")

    if card.executor_id:
        executor = await User.get_by_key('user_id', card.executor_id)
        if executor:

            # Удалить исполнителя из карточки
            if executor.tasker_id and card.task_id:
                async with kaiten as kc:
                    await kc.remove_card_member(
                        card_id=card.task_id,
                        user_id=executor.tasker_id
                    )

            # Уведомление исполнителю и закрытие сцен
            if executor.telegram_id:
                if who_changed == 'admin':
                    await asyncio.create_task(
                        notify_user(
                            executor.telegram_id,
                            "🎇 Задание возвращено на форум задач."
                        )
                    )

                await close_card_related_scenes(str(card.card_id))

    # Отмена всех тасков и установка напоминаний
    # Обновление карточки в базе
    async with session_factory() as session:
        await cancel_card_tasks(
            session=session,
            card_id=str(card.card_id)
        )

        await schedule_card_notifications(
            session=session,
            card=card
        )

        await card.update(
            session,
            status=CardStatus.pass_,
            executor_id=None
        )

        await session.commit()

    # Удаление всех превью сообщений
    async with session_factory() as delete_session:
        complete_messages = await card.get_complete_preview_messages(session=delete_session)
        if complete_messages:
            await delete_all_complete_previews(complete_messages)

    # Комментарий и обновление колонки 
    async with kaiten as kc:
        await kc.add_comment(
            card_id=card.task_id,
            text="📤 Задача возвращена на форум задач."
        )

        await kc.update_card(
            card.task_id,
            board_id=BOARD_QUEUE_ID,
            column_id=COLUMN_QUEUE_FORUM_ID
        )

    # Обновление сцены просмотра задачи
    await update_task_scenes(
        card_id=str(card.card_id),
        scene_name=SceneNames.VIEW_TASK
    )

    if res := await card.get_forum_message():
        await delete_forum_message(str(card.card_id))
        message_id, _ = await send_forum_message(str(card.card_id))

        if message_id:
            forum_message = await card.get_forum_message()
            if forum_message:
                await forum_message.update(message_id=message_id)
            else:
                await CardMessage.create(
                    card_id=card.card_id,
                    message_id=message_id
                )

    else:
        customer = await User.get_by_key('user_id', card.customer_id)
        if customer:
            await notify_user(
                telegram_id=customer.telegram_id,
                message=f'⚡ Задача "{card.name}" потеряла исполнителя.'
            )


async def to_edited(
          card: Optional[Card] = None,
          card_id: Optional[_UUID] = None
                  ):
    """ 1. Взятие / назаначение задачи
        Копирайтер взял задачу в работу с форума
        Или админ назначил задачу исполнителю (при создании приватный тип / назначен админом как исполнитель)
        Или админ нажал "взять в работу" в задаче

        2. Задачу вернули на доработку
        Исполнитель / редактор вернул задачу на доработку исполнителю

        Написать комментарий в кайтене +
        Обновить колонку в кайтене +
        Обновить сцены просмотра задачи tasks +
        Таски напоминаний +

        Обновить сцену редактирования задачи +
        Открыть сцену редактирования задачи исполнителю +

        Если тип public:
         Обновить сообщение на форуме +

        Если тип private и прошлый статус pass:
         Отправить уведомление заказчику +

        DOWNGRADE
        Если есть запланированные задачи:
          (статус: ready)
          Снять все запланированные задачи +

        DOWNGRADE
        Если есть отправленные "готовые варианты":
          (статус: ready)
          Удалить все complete_messages +
    """

    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")

    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")

    previous_status = card.status

    # DOWNGRADE: если статус меняется с ready, удаляем запланированные задачи и превью
    if previous_status == CardStatus.ready:
        async with session_factory() as session:
            await cancel_card_tasks(
                session=session,
                card_id=str(card.card_id)
            )

            await schedule_card_notifications(
                session=session,
                card=card
            )

    complete_messages = await card.get_complete_preview_messages()
    if complete_messages:
        await delete_all_complete_previews(complete_messages)

    # Обновление карточки в базе
    await card.update(status=CardStatus.edited)

    # Комментарий и обновление колонки в кайтене
    if card.task_id and card.task_id != 0:
        async with kaiten as kc:
            await kc.add_comment(
                card_id=card.task_id,
                text=Messages.TASK_TAKEN
            )

            await kc.update_card(
                card.task_id,
                board_id=BOARD_IN_PROGRESS_ID,
                column_id=COLUMN_IN_PROGRESS_EDITED_ID
            )

    # Обновление сцены просмотра задачи
    await update_task_scenes(
        card_id=str(card.card_id),
        scene_name=SceneNames.VIEW_TASK
    )

    # Обновление сообщения на форуме для public задач
    if await card.get_forum_message():
        await update_forum_message(
            str(card.card_id)
        )

    # Уведомление заказчику для private задач при взятии в работу
    elif previous_status == CardStatus.pass_:
        customer = await User.get_by_key('user_id', card.customer_id)
        if customer and customer.role != UserRole.admin:
            await notify_user(
                telegram_id=customer.telegram_id,
                message=f'🎯 Задача "{card.name}" взята в работу.'
            )

async def to_review(
          card: Optional[Card] = None,
          card_id: Optional[_UUID] = None
                  ):
    """ Отправка задания на редактирование 

        Написать комментарий в кайтене +
        Обновить колонку в кайтене +
        Обновить сцены просмотра задачи tasks +
        Очистить таски отправки +

        Обновить сцену редактирования задачи +

        Если выбран редактор:
          Отправить уведомление редактору +

        Если не выбран редактор:
          Переотправить сообщение на форум с кнопкой для редакторов "взять задание" +

          Отправить уведомление редакторам +

        DOWNGRADE
        Если есть запланированные задачи:
          (статус: ready)
          Снять все запланированные задачи +

        DOWNGRADE
        Если есть отправленные "готовые варианты":
          (статус: ready)
          Удалить все complete_messages +
    """

    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")

    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")
    
    previous_status = card.status

    # DOWNGRADE: если статус меняется с ready, удаляем запланированные задачи и превью
    if previous_status == CardStatus.ready:
        async with session_factory() as session:
            await cancel_card_tasks(
                session=session,
                card_id=str(card.card_id)
            )

    async with session_factory() as delete_session:
        complete_messages = await card.get_complete_preview_messages(session=delete_session)
        if complete_messages:
            await delete_all_complete_previews(complete_messages)

    # Обновление карточки в базе
    await card.update(status=CardStatus.review)

    # Комментарий и обновление колонки в кайтене
    if card.task_id and card.task_id != 0:
        async with kaiten as kc:
            await kc.add_comment(
                card_id=card.task_id,
                text="🔍 Задача отправлена на проверку"
            )

            await kc.update_card(
                card.task_id,
                board_id=BOARD_IN_PROGRESS_ID,
                column_id=COLUMN_IN_PROGRESS_REVIEW_ID
            )

    # Обновление сцены просмотра задачи
    await update_task_scenes(
        card_id=str(card.card_id),
        scene_name=SceneNames.VIEW_TASK
    )

    # Удаление старого сообщения с форума
    if await card.get_forum_message():
        if await delete_forum_message(str(card.card_id)):
            forum_mes = await card.get_messages(message_type='forum')
            if forum_mes:
                for mes in forum_mes:
                    await mes.delete()

    # Создание нового сообщения на форуме со статусом review
    await card.refresh()
    message_id, _ = await send_forum_message(
        str(card.card_id)
    )

    if message_id:
        forum_mes = await card.get_messages(message_type='forum')
        if forum_mes:
            mes = forum_mes[0]
            await mes.update(message_id=message_id)
        else:
            mes = await CardMessage.create(
                card_id=card.card_id,
                message_id=message_id,
                message_type='forum'
            )

    # Уведомления редакторам и админам
    recipients = []

    if card.editor_id:
        editor = await User.get_by_key('user_id', card.editor_id)
        if editor and editor.telegram_id:
            recipients.append(editor.user_id)
    else:
        customer = await User.get_by_key('user_id', card.customer_id)
        if customer and customer.role == UserRole.admin:
            recipients.append(card.customer_id)
        else:
            admins = await User.filter_by(role=UserRole.admin)
            for admin in admins:
                recipients.append(admin.user_id)

        comment = f'⚡ Появилась задача на проверку: {card.name}. Вы получили это уведомление, так как в задача ищет своего редактора.'
        editors = await User.filter_by(role=UserRole.editor)
        listeners = [
            editor.user_id for editor in editors 
            if editor.user_id != card.customer_id
        ]

        await notify_users(
            list(listeners),
            comment
        )

    msg = f"🔔 Задача требует проверки!\n\n📝 {card.name}\n\nПожалуйста, проверьте задачу и измените статус."
    await notify_users(recipients, msg)

async def to_ready(
          card: Optional[Card] = None,
          card_id: Optional[_UUID] = None
                  ):
    """ Завершение работы над задачей

        Написать комментарий в кайтене +
        Обновить колонку в кайтене +
        Обновить сцены просмотра задачи tasks +

        Закрыть сцену редактирования задачи всем +

        Очищаем таски отправки и напоминаний +
        Если need_send:
         Планируем задачи отправки +

        Переотправка сообщения на форуме +
        Отправляем / редактируем превью постов +

        Уведомляем заказчика о готовности задачи (если завершил не сам заказчик) +
        Удаляем сообщение дизайнерам +

    """

    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")

    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")

    # Обновление карточки в базе
    await card.update(status=CardStatus.ready)

    # Комментарий и обновление колонки в кайтене
    if card.task_id and card.task_id != 0:
        async with kaiten as kc:
            await kc.add_comment(
                card_id=card.task_id,
                text="✅ Задача готова к публикации"
            )

            await kc.update_card(
                card.task_id,
                board_id=BOARD_IN_PROGRESS_ID,
                column_id=COLUMN_IN_PROGRESS_READY_ID
            )

    # Закрытие сцены редактирования у исполнителя
    if card.executor_id:
        executor = await User.get_by_key('user_id', card.executor_id)
        if executor and executor.telegram_id:
            await close_user_scene(executor.telegram_id)

    # Очищаем все таски и планируем новые
    async with session_factory() as session:
        await cancel_card_tasks(
            session=session,
            card_id=str(card.card_id)
        )

        # Планируем задачи публикации только если need_send = True
        await card.refresh()
        if card.need_send:
            await schedule_post_tasks(session, card)
            logger.info(f"Запланированы задачи отправки для карточки {card.card_id}")
        else:
            # Если не нужно отправлять, сразу переводим в sent
            await card.update(status=CardStatus.sent)
            logger.info(f"Карточка {card.card_id} не требует отправки, статус изменен на sent")
            return

        await session.commit()

    # Обновление сцены просмотра задачи
    await update_task_scenes(
        card_id=str(card.card_id),
        scene_name=SceneNames.VIEW_TASK
    )

    # Обновление сообщения на форуме
    await card.refresh()
    message_id, _ = await update_forum_message(
        str(card.card_id)
    )
    if message_id:
        forum_mes = await card.get_messages(message_type='forum')
        if forum_mes:
            for mes in forum_mes:
                await mes.update(message_id=message_id)

    # Отправка превью постов для каждого клиента: удаляем старые и создаём новые
    await card.refresh()
    async with session_factory() as preview_session:
        # Получаем и удаляем все связанные сообщения превью (включая новые типы)
        complete_messages = await card.get_complete_preview_messages(session=preview_session)
        if complete_messages:
            try:
                await delete_all_complete_previews(complete_messages)
            except Exception as e:
                logger.error(f"Ошибка при удалении старых превью для карточки {card.card_id}: {e}")

        clients = card.clients or []
        for client_key in clients:
            try:
                # Всегда создаём новые превью (после удаления старых)
                await send_complete_preview(str(card.card_id), client_key, session=preview_session)
            except Exception as e:
                logger.error(f"Ошибка отправки превью для карточки {card.card_id}, клиент {client_key}: {e}")

        # Сохраняем изменения
        await preview_session.commit()

        logger.info(f"Отправлены превью постов для карточки {card.card_id}")

    # Уведомление заказчику о готовности задачи
    if card.customer_id:
        customer = await User.get_by_key(
            'user_id', card.customer_id)
        if customer and customer.telegram_id:
            deadline_str = card.deadline.strftime('%d.%m.%Y %H:%M') if card.deadline else 'Не установлен'
            message_text = (
                f"✅ Задача готова!\n\n"
                f"📝 Название: {card.name}\n"
                f"⏰ Дедлайн: {deadline_str}\n\n"
                f"Задача готова к публикации."
            )
            await notify_user(customer.telegram_id, message_text)

    # Удаление сообщения дизайнерам (prompt_message)
    if card.prompt_message:
        try:
            await delete_forum_message_by_id(card.prompt_message)
            await card.update(prompt_message=None)
            logger.info(f"Удалено сообщение дизайнерам для карточки {card.card_id}")
        except Exception as e:
            logger.error(f"Ошибка удаления сообщения дизайнерам: {e}")

async def to_sent(
          card: Optional[Card] = None,
          card_id: Optional[_UUID] = None
                  ):
    """ Задача отправлена в каналы

        Написать комментарий в кайтене +
        Обновить сцены просмотра задачи tasks +
        Обновить сцену редактирования задачи +

        Удалить сообщение с форума +

        Увеличить счетчик выполненных задач исполнителя +
        Увеличить счетчик проверенных задач редактора +

        Удалить задачу из базы
    """

    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")

    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")

    # Обновление карточки в базе
    await card.update(status=CardStatus.sent)

    # Комментарий в кайтене
    if card.task_id and card.task_id != 0:
        async with kaiten as kc:
            await kc.add_comment(
                card_id=card.task_id,
                text="🚀 Задача выполнена и отправлена!"
            )

    # Удаление сообщения с форума
    if await card.get_forum_message():
        if await delete_forum_message(str(card.card_id)):
            forum_mes = await card.get_messages(message_type='forum')
            if forum_mes:
                for mes in forum_mes:
                    await mes.delete()

    # Обновление сцены просмотра задачи
    await update_task_scenes(
        card_id=str(card.card_id),
        scene_name=SceneNames.VIEW_TASK
    )

    # Увеличение счетчика выполненных задач у исполнителя
    if card.executor_id:
        executor = await User.get_by_key('user_id', card.executor_id)
        if executor:
            await executor.update(
                tasks=executor.tasks + 1,
                task_per_month=executor.task_per_month + 1,
                task_per_year=executor.task_per_year + 1
            )
            logger.info(f"Увеличен счетчик задач для исполнителя {executor.user_id}")

    # Увеличение счетчика проверенных задач у редактора
    await increment_reviewers_tasks(card)

    # Закрытие всех сцен, связанных с этой задачей
    await close_card_related_scenes(str(card.card_id))

    await card.delete()