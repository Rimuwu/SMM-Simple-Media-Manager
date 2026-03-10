import asyncio
from typing import Any, Literal, Optional
from uuid import UUID as _UUID
from database.connection import session_factory
from modules.enums import UserRole
from modules.json_utils import open_clients, open_settings

from models.User import User
from modules.tasks.scheduler import schedule_card_notifications, cancel_card_tasks, schedule_post_tasks

from modules.card.card_service import increment_reviewers_tasks
from modules.exec.executors_client import (
    send_forum_message, update_forum_message, delete_forum_message, delete_forum_message_by_id,
    send_complete_preview, delete_all_complete_previews,
    close_user_scene, update_task_scenes, close_card_related_scenes,
    notify_user, notify_users
)
from app.modules.components.logs import logger
from app.models.Message import CardMessage

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.card.Card import Card, CardStatus

settings = open_settings() or {}

async def to_pass(
          card: Optional['Card'] = None,
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

    task = await card.get_task()
    executor_id = task.executor_id if task else None
    if executor_id:
        executor = await User.get_by_key('user_id', executor_id)
        if executor:

            # Уведомление исполнителю и закрытие сцен
            if executor.telegram_id:
                if who_changed == 'admin':
                    await asyncio.create_task(
                        notify_user(
                            executor.telegram_id,
                            "🎇 Задание возвращено на форум задач.",
                            card_id=str(card.card_id)
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
            status=CardStatus.pass_
        )

        await session.commit()

    # Удаление всех превью сообщений
    async with session_factory() as delete_session:
        complete_messages = await card.get_complete_preview_messages(session=delete_session)
        if complete_messages:
            await delete_all_complete_previews(complete_messages)

    # Обновление сцены просмотра задачи
    await update_task_scenes(str(card.card_id))

    if await card.get_forum_message():
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
        task = await card.get_task()
        customer_id = task.customer_id if task else None
        if customer_id:
            customer = await User.get_by_key('user_id', customer_id)
            if customer:
                await notify_user(
                    customer.telegram_id,
                    message=f'⚡ Задача "{card.name}" потеряла исполнителя.',
                    card_id=str(card.card_id)
                )


async def to_edited(
          card: Optional['Card'] = None,
          card_id: Optional[_UUID] = None,
          who_changed: Any = None
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

    # Обновление сцены просмотра задачи
    await update_task_scenes(str(card.card_id))

    # Обновление сообщения на форуме для public задач
    if await card.get_forum_message():
        await update_forum_message(
            str(card.card_id)
        )

    # Уведомление заказчику для private задач при взятии в работу
    elif previous_status == CardStatus.pass_:
        task = await card.get_task()
        customer_id = task.customer_id if task else None
        if customer_id:
            customer = await User.get_by_key('user_id', customer_id)
            if customer and customer.role != UserRole.admin:
                await notify_user(
                    customer.telegram_id,
                    message=f'🎯 Задача "{card.name}" взята в работу.',
                    card_id=str(card.card_id)
                )

async def to_review(
          card: Optional['Card'] = None,
          card_id: Optional[_UUID] = None,
          who_changed: Any = None
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

    # Обновление сцены просмотра задачи
    await update_task_scenes(str(card.card_id))

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

    task = await card.get_task()
    customer_id = task.customer_id if task else None

    # Нет редактора на уровне карточки — уведомляем заказчика/админов
    if customer_id:
        customer = await User.get_by_key('user_id', customer_id)
        if customer and customer.role == UserRole.admin:
            recipients.append(customer_id)
        else:
            admins = await User.filter_by(role=UserRole.admin)
            for admin in admins:
                recipients.append(admin.user_id)
    else:
        admins = await User.filter_by(role=UserRole.admin)
        for admin in admins:
            recipients.append(admin.user_id)

    comment = f'⚡ Появилась задача на проверку: {card.name}. Вы получили это уведомление, так как задача ищет своего редактора.'
    editors = await User.filter_by(role=UserRole.editor)
    listeners = [
        editor.user_id for editor in editors
        if customer_id is None or editor.user_id != customer_id
    ]

    await notify_users(
        list(listeners),
        comment,
        card_id=str(card.card_id)
    )

    msg = f"🔔 Задача требует проверки!\n\n📝 {card.name}\n\nПожалуйста, проверьте задачу и измените статус."
    await notify_users(recipients, msg, card_id=str(card.card_id))

async def to_ready(
          card: Optional['Card'] = None,
          card_id: Optional[_UUID] = None,
          who_changed: Any = None
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

    # Закрытие сцены редактирования у исполнителя из задания
    task = await card.get_task()
    executor_id = task.executor_id if task else None
    if executor_id:
        executor = await User.get_by_key('user_id', executor_id)
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
            logger.info(f"Карточка {card.card_id} не требует отправки — выполняем финализацию (to_sent)")
            await to_sent(card=card)
            return

        await session.commit()

    # Обновление сцены просмотра задачи
    await update_task_scenes(str(card.card_id))

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
    task = await card.get_task()
    customer_id = task.customer_id if task else None
    if customer_id:
        customer = await User.get_by_key('user_id', customer_id)

        if customer and customer.telegram_id:
            send_time = card.send_time.strftime('%d.%m.%Y %H:%M') if card.send_time else 'Не установлен'
            
            client_settings = open_clients() or {}
            clients = card.clients or []
            client_names = [
                client_settings[client]['label'] for client in clients if client in list(client_settings.keys())
            ]

            message_text = (
                f"✅ Задача готова!\n\n"
                f"📝 Название: {card.name}\n"
                f"⏰ Время отправки: {send_time}\n"
                f"🕹 Клиенты: {', '.join(client_names)}\n\n"
                f"Задача готова к публикации. Вы можете просмотреть итоговый вид поста и дать комментарий копирайтеру."
            )
            await notify_user(customer.telegram_id, message_text, card_id=str(card.card_id))

    # Удаление сообщения дизайнерам (prompt_message)
    if card.prompt_message:
        try:
            await delete_forum_message_by_id(card.prompt_message)
            await card.update(prompt_message=None)
            logger.info(f"Удалено сообщение дизайнерам для карточки {card.card_id}")
        except Exception as e:
            logger.error(f"Ошибка удаления сообщения дизайнерам: {e}")

async def to_sent(
          card: Optional['Card'] = None,
          card_id: Optional[_UUID] = None,
          who_changed: Any = None
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

    # Удаление сообщения с форума
    if await card.get_forum_message():
        if await delete_forum_message(str(card.card_id)):
            forum_mes = await card.get_messages(message_type='forum')
            if forum_mes:
                for mes in forum_mes:
                    await mes.delete()

    # Увеличение счетчика выполненных задач у исполнителя задания
    task = await card.get_task()
    executor_id = task.executor_id if task else None
    if executor_id:
        executor = await User.get_by_key('user_id', executor_id)
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