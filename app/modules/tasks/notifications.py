from models.Card import Card, CardStatus
from models.User import User
from modules.enums import UserRole
from modules.exec import executor_bridge
from datetime import datetime
import html
from modules.json_utils import open_settings, open_clients
from modules.logs import logger


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
    if card.status in [CardStatus.ready, CardStatus.sent]:
        logger.info(f"Карточка {card.card_id} имеет статус ready или sent, напоминание не отправляется")
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
        message_text = f"⏰ Напоминание о дедлайне\n📝 Задача: {card.name}\n⏰ Дедлайн: {deadline_str}\n\nОсталось 2 дня!"

        # Отправляем уведомление
        await executor_bridge.notify_user(executor.telegram_id, message_text)
        
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
        message_text = f"⏰ Дедлайн прошел!\n📝 Задача: {card.name}\n\nЗадача просрочена!"

        await executor_bridge.notify_user(
            group_forum, message_text, reply_to=await card.get_forum_message()
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

        await executor_bridge.notify_user(
            group_forum, message_text, reply_to=await card.get_forum_message()
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
                await executor_bridge.notify_user(admin.telegram_id, message_text)
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления админу {admin.telegram_id}: {e}")
        
        # Также отправляем на форум
        await send_forum_no_executor_alert(card, **kwargs)
        
        logger.info(f"Уведомления о карточке {card.card_id} отправлены всем админам")
        
    except Exception as e:
        logger.error(f"Ошибка отправки уведомлений админам для карточки {card.card_id}: {e}", exc_info=True)


async def send_post_now(card_id: str, client_key: str, **kwargs):
    """
    Немедленно отправить пост через исполнителя.
    Используется для telegram_executor и vk_executor, которые не поддерживают
    нативную отложенную отправку.
    
    Вся генерация контента и работа с исполнителями происходит на стороне executors API.
    
    Args:
        card_id: ID карточки с контентом
        client_key: Ключ клиента из clients.json
        **kwargs: Дополнительные параметры
    """
    logger.info(f"Немедленная отправка поста для карточки {card_id}, клиент: {client_key}")
    
    try:
        # Загружаем связанные данные через явную сессию, чтобы избежать lazy-loading вне greenlet
        from database.connection import session_factory
        content = 'nothing'
        clients_settings = {}
        entities_for_client = []

        async with session_factory() as s:
            # Contents: выбираем последний (по created_at) для каждого client_key
            card = await Card.get_by_key('card_id', card_id, session=s)
            if not card:
                logger.warning(f"Карточка {card_id} не найдена при отправке поста")
                return
            contents = await card.get_content(session=s)
            content_map: dict[str, tuple[str, object]] = {}
            for c in contents:
                key = c.client_key or 'all'
                created = getattr(c, 'created_at', None)
                prev = content_map.get(key)
                if not prev or (created and prev[1] and created > prev[1]):
                    content_map[key] = (c.text, created)
            content_dict = {k: v[0] for k, v in content_map.items()}
            content = content_dict.get(client_key) or content_dict.get('all') or 'nothing'

            # Clients settings
            settings_entries = await card.get_clients_settings(session=s)
            clients_settings = {}
            for s_entry in settings_entries:
                key = s_entry.client_key or 'all'
                clients_settings.setdefault(key, {}).update(s_entry.data or {})
            # merge global and specific
            merged_settings = clients_settings.get('all', {}).copy()
            merged_settings.update(clients_settings.get(client_key, {}))
            clients_settings = merged_settings

            # Entities
            entities_entries = await card.get_entities(session=s)
            entities_for_client = []
            for ent in entities_entries:
                if ent.client_key == client_key or ent.client_key is None:
                    entities_for_client.append(ent.to_dict())

        # делегируем всю работу helper-методу
        from modules.post_sender import send_post

        response = await send_post(
            card_id=str(card.card_id),
            client_key=client_key,
            content=content,
            tags=card.tags,
            post_images=card.post_images or [],
            settings=clients_settings,
            entities=entities_for_client,
        )
        
        if response.get('success'):
            logger.info(f"Пост для карточки {card.card_id} отправлен, клиент: {client_key}")

            # Save sent message ids returned by executor (categorize and persist as CardMessage)
            try:
                sent = response.get('sent_message_ids') or {}
                # expected shape: { 'send_main': [ids], 'send_entity': [ids], 'send_other': [ids] }
                for tname, mids in (sent.items() if isinstance(sent, dict) else []):
                    if not mids:
                        continue
                    msg_type = None
                    if tname == 'send_main':
                        msg_type = 'send_main'
                    elif tname == 'send_entity':
                        msg_type = 'send_entity'
                    elif tname == 'send_other':
                        msg_type = 'send_other'

                    if msg_type:
                        for mid in (mids or []):
                            try:
                                await card.add_message(message_type=msg_type, message_id=int(mid), data_info=client_key)
                            except Exception as e:
                                logger.error(f"Cannot save CardMessage {msg_type} {mid} for card {card.card_id}: {e}")
            except Exception as e:
                logger.error(f"Error while saving sent message ids for card {card.card_id}: {e}")

            # Добавляем логи в задачу финализации (если есть)
            try:
                logs = response.get('logs', [])
                await append_logs_to_finalize_task(str(card.card_id), logs)
            except Exception as e:
                logger.error(f"Ошибка при добавлении логов в задачу финализации: {e}")

            
        else:
            logger.error(f"Ошибка отправки поста: {response}")
            logs = response.get('logs', [])
            # Сохраняем логи в задаче финализации для последующего анализа
            try:
                await append_logs_to_finalize_task(str(card.card_id), logs)
            except Exception as e:
                logger.error(f"Ошибка при добавлении логов в задачу финализации: {e}")
            await notify_admins_about_post_failure(card, client_key, response.get('error', 'Unknown error'),
                                                   logs)

    except Exception as e:
        logger.error(f"Ошибка при отправке поста для карточки {card.card_id}: {e}", exc_info=True)
        await notify_admins_about_post_failure(card, client_key, str(e))

def normalize_logs(logs: list[dict]) -> str:
    """
    Преобразовать список логов в читабельную многострочную строку.
    Ограничивает количество записей и длину итоговой строки, всегда возвращает str.
    """
    if not logs:
        return "Нет логов."

    lines = []
    # Ограничение по количеству записей, чтобы сообщение не было огромным
    max_entries = 20
    for i, entry in enumerate(logs[:max_entries]):
        if isinstance(entry, dict):
            ts = entry.get('time') or entry.get('timestamp') or entry.get('date') or ''
            level = entry.get('level') or entry.get('lvl') or ''
            msg = entry.get('message') or entry.get('msg') or ''
            msg_str = str(msg).replace('\n', ' ').strip()
            part = f"{i + 1}. {ts} [{level}] {msg_str}".strip()
        else:
            part = f"{i + 1}. {str(entry)}"
        lines.append(part)

    if len(logs) > max_entries:
        lines.append(f"... и ещё {len(logs) - max_entries} записей")

    result = "\n".join(lines)

    # Ограничение общей длины (например, чтобы помещалось в уведомление)
    max_len = 3000
    if len(result) > max_len:
        result = result[: max_len - 3] + "..."

    return result

async def notify_admins_about_post_failure(
    card: Card, client_key: str, error: str, logs: list[dict] | None = None
    ):
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
        
        logs_text = normalize_logs(logs) if logs else "Нет логов."
        escaped_logs = html.escape(logs_text)

        if logs:
            # Скрываем длинные логи в спойлере внутри блока цитаты
            logs_block = f"\n<blockquote><pre>{escaped_logs}</pre></blockquote>\n"
        else:
            logs_block = ""

        message_text = (
            f"❌ <b>Ошибка публикации поста</b>\n\n"
            f"📝 Задача: {html.escape(str(card.name))}\n"
            f"📢 Канал: {html.escape(str(client_key))}\n"
            f"⚠️ Ошибка: {html.escape(str(error))}\n"
            f"{logs_block}"
            f"❗ Требуется ручная публикация!"
        )

        for admin in admins:
            try:
                await executor_bridge.notify_user(admin.telegram_id, message_text, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Ошибка уведомления админа {admin.telegram_id}: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка уведомления админов об ошибке публикации: {e}", exc_info=True)


async def append_logs_to_finalize_task(card_id: str, logs: list[dict] | None):
    """Добавить логи в аргументы задачи финализации публикации карточки.

    Если задача финализации найдена, её поле `arguments` получает ключ `logs` со списком записей.
    Если ключ уже есть - новые записи добавляются в конец.
    """
    if not logs:
        return

    try:
        from models.ScheduledTask import ScheduledTask
        from database.connection import session_factory
        from sqlalchemy import select, update
        from uuid import UUID as PyUUID

        try:
            card_uuid = PyUUID(card_id) if isinstance(card_id, str) else card_id
        except Exception:
            logger.error(f"Невалидный card_id для добавления логов: {card_id}")
            return

        async with session_factory() as session:
            stmt = select(ScheduledTask).where(
                ScheduledTask.card_id == card_uuid,
                ScheduledTask.function_path == "modules.tasks.notifications.finalize_card_publication"
            )
            res = await session.execute(stmt)
            task = res.scalars().first()
            if not task:
                logger.warning(f"Задача финализации для карточки {card_id} не найдена, логи не добавлены")
                return

            args = task.arguments or {}
            existing_logs = args.get('logs') or []
            if not isinstance(existing_logs, list):
                existing_logs = [existing_logs]

            combined = existing_logs + logs

            # Сохраняем (можно добавить ограничение размера при необходимости)
            args['logs'] = combined

            upd = update(ScheduledTask).where(ScheduledTask.task_id == task.task_id).values(arguments=args)
            await session.execute(upd)
            await session.commit()

            logger.info(f"Добавлено {len(logs)} записей логов в задачу финализации карточки {card_id}")

    except Exception as e:
        logger.error(f"Ошибка добавления логов в задачу финализации для карточки {card_id}: {e}", exc_info=True)


async def finalize_card_publication(card_id: str, **kwargs):
    """
    Финализировать публикацию карточки после отправки всех постов.
    Меняет статус на sent, удаляет сообщение с форума, увеличивает счётчики задач исполнителя и отправляет отчёт админам.
    
    Args:
        card: Карточка
        **kwargs: Дополнительные параметры
    """
    logger.info(f"Финализация публикации карточки {card_id}")
    
    try:
        # Обновляем статус карточки на sent
        card = await Card.get_by_key('card_id', card_id)
        if not card:
            logger.warning(f"Карточка {card_id} не найдена при финализации")
            return
        await card.update(status=CardStatus.sent)
        logger.info(f"Статус карточки {card.card_id} изменен на sent")
        
        # Создаём задачу на удаление карточки через 2 дня
        try:
            from models.ScheduledTask import ScheduledTask
            from database.connection import session_factory
            from modules.timezone import now_naive as moscow_now
            from datetime import timedelta
            from uuid import UUID as PyUUID
            
            delete_at = moscow_now() + timedelta(days=0.5)
            card_uuid = card.card_id if isinstance(card.card_id, PyUUID) else PyUUID(str(card.card_id))
            
            async with session_factory() as session:
                task = ScheduledTask(
                    card_id=card_uuid,
                    function_path="modules.tasks.notifications.delete_sent_card",
                    execute_at=delete_at,
                    arguments={"card_id": str(card.card_id)}
                )
                session.add(task)
                await session.commit()
                logger.info(f"Создана задача удаления карточки {card.card_id} на {delete_at}")
        except Exception as e:
            logger.error(f"Ошибка создания задачи удаления: {e}")
        

        try:
            from modules.card.status_changers import to_sent
            await to_sent(card=card)
        except Exception as e:
            logger.error(f"Ошибка смены статуса карточки {card.card_id}: {e}")

        try:
            clients_cfg = open_clients() or {}
            src_client_key = None
            for ck in (card.clients or []):
                cfg = clients_cfg.get(ck)
                if not cfg:
                    continue
                ex_name = cfg.get('executor_name') or cfg.get('executor')
                if ex_name == 'telegram_executor':
                    src_client_key = ck
                    break

            if src_client_key:
                sent_msgs = await card.get_messages()
                post_msgs = [m for m in sent_msgs if m.message_type == 'send_main' and m.data_info == src_client_key]

                if not post_msgs:
                    complete_msgs = await card.get_complete_messages_by_client(client_key=src_client_key)
                    post_msgs = [m for m in complete_msgs if m.message_type == 'complete_post']

                if post_msgs:
                    src_msg_id = int(post_msgs[0].message_id)
                    settings = open_settings() or {}
                    source_chat = settings.get('complete_topic')

                    if source_chat and card.tags:
                        try:
                            await executor_bridge.forward_first_by_tags(
                                source_chat_id=source_chat,
                                message_id=src_msg_id,
                                tags=card.tags,
                                source_client_key=src_client_key
                            )
                            logger.info(f"forward-first-by-tags called during finalize for card {card.card_id}")
                        except Exception as e:
                            logger.error(f"Error calling forward-first-by-tags during finalize for card {card.card_id}: {e}", exc_info=True)
                else:
                    logger.debug(f"No post/preview message for client {src_client_key} (card {card.card_id}), skipping forward-first-by-tags")
        except Exception as e:
            logger.error(f"Error while preparing forward-first-by-tags in finalize_card_publication for card {card.card_id}: {e}", exc_info=True)

        # Получаем список каналов для отчёта
        clients_str = ", ".join(card.clients) if card.clients else "Не указаны"

        logs = normalize_logs(kwargs.get('logs', []))

        # Отправляем отчёт админам
        admins = await User.filter_by(role=UserRole.admin)
        if admins:
            message_text = (
                f"✅ Публикация завершена\n\n"
                f"📝 Задача: {card.name}\n"
                f"📢 Каналы: {clients_str}\n"
                f"⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"📄 Логи публикации:\n<pre>{html.escape(logs)}</pre>"
            )
            
            for admin in admins:
                try:
                    await executor_bridge.notify_user(admin.telegram_id, message_text, parse_mode='HTML')
                except Exception as e:
                    logger.error(f"Ошибка уведомления админа {admin.telegram_id}: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка финализации публикации карточки {card.card_id}: {e}", exc_info=True)

# Логика генерации лидерборда перемещена в исполнителя (executors).
# Логика лидерборда: executor_bridge.send_leaderboard вызывается перед сбросом счётчика.


async def reset_monthly_tasks():
    """
    Сбросить месячный счетчик задач у всех пользователей.
    Отправить лидерборд на форум перед сбросом.
    После выполнения создаёт следующую задачу сброса.
    """
    logger.info("Запуск сброса месячного счетчика задач")
    
    try:
        # Запрос исполнителю на отправку лидерборда перед сбросом
        settings = open_settings()
        group_forum = settings.get('group_forum')

        if group_forum:
            await executor_bridge.send_leaderboard(
                chat_id=group_forum,
                period="month",
                reply_to=settings.get('forum_topic')
            )
            logger.info("Запрошена отправка лидерборда месяца исполнителем")

        # Сбрасываем счетчики
        users = await User.filter_by()
        for user in users:
            await user.update(task_per_month=0)

        logger.info(f"Месячный счетчик сброшен у {len(users)} пользователей")

        # Создаём следующую задачу сброса
        from modules.tasks.reset_tasks import check_and_create_monthly_reset_task
        await check_and_create_monthly_reset_task()

    except Exception as e:
        logger.error(f"Ошибка сброса месячного счетчика: {e}", exc_info=True)


async def reset_yearly_tasks():
    """
    Сбросить годовой счетчик задач у всех пользователей.
    Отправить лидерборд на форум перед сбросом.
    После выполнения создаёт следующую задачу сброса.
    """
    logger.info("Запуск сброса годового счетчика задач")
    
    try:
        # Запрос исполнителю на отправку лидерборда перед сбросом
        settings = open_settings()
        group_forum = settings.get('group_forum')
        
        if group_forum:
            await executor_bridge.send_leaderboard(
                chat_id=group_forum,
                period="year",
                extra_text="С новым годом дизановры!",
                reply_to=settings.get('forum_topic')
            )
            logger.info("Запрошена отправка лидерборда года исполнителем")

        # Сбрасываем счетчики (годовой и месячный)
        users = await User.filter_by()
        for user in users:
            await user.update(task_per_year=0)

        logger.info(f"Годовой счетчик сброшен у {len(users)} пользователей")

        # Создаём следующую задачу сброса
        from modules.tasks.reset_tasks import check_and_create_yearly_reset_task
        await check_and_create_yearly_reset_task()

    except Exception as e:
        logger.error(f"Ошибка сброса годового счетчика: {e}", exc_info=True)
