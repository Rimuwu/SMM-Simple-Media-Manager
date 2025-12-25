from models.Card import Card, CardStatus
from models.User import User
from global_modules.classes.enums import UserRole
from modules.api_client import executors_api
from modules.constants import ApiEndpoints
from datetime import datetime
import html
from global_modules.json_get import open_settings
from modules.logs import brain_logger as logger

# logger = logging.getLogger(__name__)


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
        message_text = f"⏰ Дедлайн прошел!\n📝 Задача: {card.name}\n\nЗадача просрочена!"

        await executors_api.post(
            ApiEndpoints.NOTIFY_USER,
            data={
                "user_id": group_forum,
                "message": message_text,
                "reply_to": await card.get_forum_message()
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
                "message": message_text,
                "reply_to": await card.get_forum_message()
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
        # Получаем контент для клиента (сначала специфичный, потом общий)
        content_dict = card.content if isinstance(card.content, dict) else {}
        content = content_dict.get(client_key) or content_dict.get('all') or 'nothing'

        clients_settings: dict = card.clients_settings.get('all', {})
        clients_settings.update(card.clients_settings.get(client_key, {}))

        # Получаем entities для этого клиента
        entities_for_client = []
        if card.entities:
            entities_for_client = card.entities.get(client_key, [])

        # Отправляем запрос на немедленную публикацию - всю логику выполняет executors API
        response, status = await executors_api.post(
            "/post/send",
            data={
                "card_id": str(card.card_id),
                "client_key": client_key,
                "content": content,
                "tags": card.tags,
                "post_images": card.post_images or [],  # Имена файлов из Kaiten
                "settings": clients_settings,  # Дополнительные настройки для отправки
                "entities": entities_for_client  # Entities для отправки (опросы и т.д.)
            }
        )
        
        if status == 200 and response.get('success'):
            logger.info(f"Пост для карточки {card.card_id} отправлен, клиент: {client_key}")
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
                await executors_api.post(
                    ApiEndpoints.NOTIFY_USER,
                    data={
                        "user_id": admin.telegram_id,
                        "message": message_text,
                        "parse_mode": "HTML"
                    }
                )
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
                ScheduledTask.function_path == "modules.notifications.finalize_card_publication"
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


async def finalize_card_publication(card: Card, **kwargs):
    """
    Финализировать публикацию карточки после отправки всех постов.
    Меняет статус на sent, удаляет сообщение с форума, увеличивает счётчики задач исполнителя и отправляет отчёт админам.
    
    Args:
        card: Карточка
        **kwargs: Дополнительные параметры
    """
    logger.info(f"Финализация публикации карточки {card.card_id}")
    
    try:
        # Обновляем статус карточки на sent
        await card.update(status=CardStatus.sent)
        logger.info(f"Статус карточки {card.card_id} изменен на sent")
        
        # Создаём задачу на удаление карточки через 2 дня
        try:
            from models.ScheduledTask import ScheduledTask
            from database.connection import session_factory
            from global_modules.timezone import now_naive as moscow_now
            from datetime import timedelta
            from uuid import UUID as PyUUID
            
            delete_at = moscow_now() + timedelta(days=0.5)
            card_uuid = card.card_id if isinstance(card.card_id, PyUUID) else PyUUID(str(card.card_id))
            
            async with session_factory() as session:
                task = ScheduledTask(
                    card_id=card_uuid,
                    function_path="modules.notifications.delete_sent_card",
                    execute_at=delete_at,
                    arguments={"card_id": str(card.card_id)}
                )
                session.add(task)
                await session.commit()
                logger.info(f"Создана задача удаления карточки {card.card_id} на {delete_at}")
        except Exception as e:
            logger.error(f"Ошибка создания задачи удаления: {e}")
        
        # Удаляем сообщение с форума
        if await card.get_forum_message():
            try:
                await executors_api.delete(f"/forum/delete-forum-message/{card.card_id}")

                forum_message = await card.get_forum_message()
                if forum_message: await forum_message.delete()

                logger.info(f"Сообщение с форума для карточки {card.card_id} удалено")
            except Exception as e:
                logger.error(f"Ошибка удаления сообщения с форума: {e}")
        
        # Увеличиваем счётчики задач исполнителя
        if card.executor_id:
            try:
                executor = await User.get_by_key('user_id', card.executor_id)
                if executor:
                    await executor.update(
                        tasks=executor.tasks + 1,
                        task_per_month=executor.task_per_month + 1,
                        task_per_year=executor.task_per_year + 1
                    )
                    logger.info(f"Счётчики задач исполнителя {executor.user_id} увеличены")
            except Exception as e:
                logger.error(f"Ошибка увеличения счётчиков задач: {e}")
        
        # Увеличиваем tasks_checked для редакторов из editor_notes
        if card.editor_notes:
            reviewer_ids = set()
            for note in card.editor_notes:
                if not note.get('is_customer', False):
                    author_id = note.get('author')
                    if author_id:
                        reviewer_ids.add(str(author_id))
            
            for reviewer_id in reviewer_ids:
                try:
                    reviewer = await User.get_by_key('user_id', reviewer_id)
                    if reviewer:
                        await reviewer.update(tasks_checked=reviewer.tasks_checked + 1)
                        logger.info(f"Увеличен счётчик проверенных задач для редактора {reviewer.user_id}")
                except Exception as e:
                    logger.error(f"Ошибка увеличения счётчика проверенных задач для {reviewer_id}: {e}")
        
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
                    await executors_api.post(
                        ApiEndpoints.NOTIFY_USER,
                        data={
                            "user_id": admin.telegram_id,
                            "message": message_text,
                            "parse_mode": "HTML"
                        }
                    )
                except Exception as e:
                    logger.error(f"Ошибка уведомления админа {admin.telegram_id}: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка финализации публикации карточки {card.card_id}: {e}", exc_info=True)

async def get_leaderboard_text(period: str = "all") -> str:
    """
    Получить текст лидерборда.
    
    Args:
        period: "all", "year" или "month"
    
    Returns:
        Форматированный текст лидерборда
    """
    from sqlalchemy import desc
    
    # Получаем пользователей отсортированных по количеству задач
    if period == "year":
        users = await User.filter_by()  # Получаем всех
        users = sorted(users, key=lambda u: u.task_per_year, reverse=True)
        period_name = "год"
        get_tasks = lambda u: u.task_per_year

    elif period == "month":
        users = await User.filter_by()
        users = sorted(users, key=lambda u: u.task_per_month, reverse=True)
        period_name = "месяц"
        get_tasks = lambda u: u.task_per_month

    else:  # all
        users = await User.filter_by()
        users = sorted(users, key=lambda u: u.tasks, reverse=True)
        period_name = "всё время"
        get_tasks = lambda u: u.tasks
    
    # Фильтруем пользователей с 0 задачами
    users = [u for u in users if get_tasks(u) > 0]

    if not users:
        return f"🏆 Лидерборд ({period_name})\n\nПока нет выполненных задач."

    # Формируем текст
    text_lines = [f"🏆 Лидерборд ({period_name})\n"]
    
    medals = ["🥇", "🥈", "🥉"]
    for i, user in enumerate(users[:10]):  # Топ 10
        medal = medals[i] if i < 3 else f"{i + 1}."
        tasks_count = get_tasks(user)
        text_lines.append(f"{medal} ID: {user.telegram_id} — {tasks_count} задач")

    return "\n".join(text_lines)


async def reset_monthly_tasks():
    """
    Сбросить месячный счетчик задач у всех пользователей.
    Отправить лидерборд на форум перед сбросом.
    После выполнения создаёт следующую задачу сброса.
    """
    logger.info("Запуск сброса месячного счетчика задач")
    
    try:
        # Получаем и отправляем лидерборд перед сбросом
        leaderboard_text = await get_leaderboard_text("month")

        settings = open_settings()
        group_forum = settings.get('group_forum')

        if group_forum:
            await executors_api.post(
                ApiEndpoints.NOTIFY_USER,
                data={
                    "user_id": group_forum,
                    "message": f"📊 Итоги месяца:\n\n{leaderboard_text}",
                    "reply_to": settings.get('forum_topic')
                }
            )
            logger.info("Лидерборд месяца отправлен на форум")

        # Сбрасываем счетчики
        users = await User.filter_by()
        for user in users:
            await user.update(task_per_month=0)

        logger.info(f"Месячный счетчик сброшен у {len(users)} пользователей")

        # Создаём следующую задачу сброса
        from modules.reset_tasks import check_and_create_monthly_reset_task
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
        # Получаем и отправляем лидерборд перед сбросом
        leaderboard_text = await get_leaderboard_text("year")
        
        settings = open_settings()
        group_forum = settings.get('group_forum')
        
        if group_forum:
            await executors_api.post(
                ApiEndpoints.NOTIFY_USER,
                data={
                    "user_id": group_forum,
                    "message": f"📊 Итоги года:\n\n{leaderboard_text}\n\nС новым годом дизановры!",
                    "reply_to": settings.get('forum_topic')
                }
            )
            logger.info("Лидерборд года отправлен на форум")

        # Сбрасываем счетчики (годовой и месячный)
        users = await User.filter_by()
        for user in users:
            await user.update(task_per_year=0)

        logger.info(f"Годовой счетчик сброшен у {len(users)} пользователей")

        # Создаём следующую задачу сброса
        from modules.reset_tasks import check_and_create_yearly_reset_task
        await check_and_create_yearly_reset_task()

    except Exception as e:
        logger.error(f"Ошибка сброса годового счетчика: {e}", exc_info=True)
