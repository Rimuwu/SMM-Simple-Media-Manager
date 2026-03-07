"""
Клиент для работы с brain (данными БД).
В монолите заменяет HTTP-вызовы к brain-api прямыми вызовами к моделям SQLAlchemy.
"""
from typing import Optional
from uuid import UUID as _UUID
from global_modules.classes.enums import CardStatus
from modules.logs import logger


async def get_cards(task_id=None, card_id=None, status=None, customer_id=None, executor_id=None, need_check=None) -> list[dict]:
    from models.Card import Card
    from sqlalchemy import select
    from database.connection import session_factory
    async with session_factory() as session:
        query = select(Card)
        if task_id is not None: query = query.where(Card.task_id == int(task_id))
        if card_id is not None:
            try: query = query.where(Card.card_id == _UUID(str(card_id)))
            except Exception: return []
        if status is not None: query = query.where(Card.status == status)
        if customer_id is not None: query = query.where(Card.customer_id == _UUID(str(customer_id)))
        if executor_id is not None: query = query.where(Card.executor_id == _UUID(str(executor_id)))
        if need_check is not None: query = query.where(Card.need_check == need_check)
        result = await session.execute(query)
        cards = result.scalars().all()
        # Преобразуем модели в словари и добавим содержимое (content) для удобства
        out: list[dict] = []
        for c in cards:
            d = c.to_dict()
            try:
                # свойство .content возвращает словарь client_key -> text
                d['content'] = c.content
            except Exception:
                d['content'] = {}
            out.append(d)
        return out


async def update_card(card_id: str, **kwargs) -> dict | None:
    from models.Card import Card
    from datetime import datetime as _dt
    _NOTHING = "__nothing__"
    _DATETIME_FIELDS = {"deadline", "send_time"}
    updates = {k: v for k, v in kwargs.items() if v != _NOTHING}
    # Конвертируем ISO-строки в datetime для полей типа DateTime
    for field in _DATETIME_FIELDS:
        if field in updates and isinstance(updates[field], str):
            try:
                updates[field] = _dt.fromisoformat(updates[field])
            except ValueError:
                pass
    try:
        card = await Card.get_by_id(_UUID(str(card_id)))
        if not card: return None
        await card.update(**updates)
        return card.to_dict()
    except Exception as e:
        logger.error(f"Ошибка обновления карточки {card_id}: {e}"); return None


async def change_card_status(card_id: str, status: CardStatus, who_changed: str = "admin", comment=None) -> dict | None:
    from modules import status_changers
    from models.Card import Card
    try:
        card = await Card.get_by_id(_UUID(str(card_id)))
        if not card: return None
        handler = {
            CardStatus.pass_: status_changers.to_pass,
            CardStatus.in_progress: status_changers.to_in_progress,
            CardStatus.need_check: status_changers.to_need_check,
            CardStatus.in_check: status_changers.to_in_check,
            CardStatus.ready: status_changers.to_ready,
            CardStatus.sent: status_changers.to_sent,
        }.get(status)
        if handler: await handler(card=card, who_changed=who_changed)
        else: await card.update(status=status)
        return card.to_dict()
    except Exception as e:
        logger.error(f"Ошибка изменения статуса карточки {card_id}: {e}"); return None


async def add_editor_note(card_id: str, content: str, author_user_id: str, is_editor_note: bool = True) -> dict | None:
    from models.CardEditorNote import CardEditorNote
    try:
        note = await CardEditorNote.create(card_id=_UUID(str(card_id)), content=content, author=str(author_user_id))
        return note.to_dict()
    except Exception as e:
        logger.error(f"Ошибка добавления заметки редактора к карточке {card_id}: {e}"); return None


async def get_messages(card_id=None, message_type=None) -> list[dict]:
    from models.CardMessage import CardMessage
    from sqlalchemy import select
    from database.connection import session_factory
    async with session_factory() as session:
        query = select(CardMessage)
        if card_id is not None: query = query.where(CardMessage.card_id == _UUID(str(card_id)))
        if message_type is not None: query = query.where(CardMessage.message_type == message_type)
        result = await session.execute(query)
        return [m.to_dict() for m in result.scalars().all()]


async def set_content(card_id: str, content: str, client_key=None) -> bool:
    from models.CardContent import CardContent
    from sqlalchemy import select
    from database.connection import session_factory
    try:
        async with session_factory() as session:
            q = select(CardContent).where(CardContent.card_id == _UUID(str(card_id)))
            if client_key is not None: q = q.where(CardContent.client_key == client_key)
            result = await session.execute(q)
            existing = result.scalar_one_or_none()
            if existing:
                await existing.update(session=session, text=content)
            else:
                session.add(CardContent(card_id=_UUID(str(card_id)), client_key=client_key, text=content))
            await session.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка сохранения контента карточки {card_id}: {e}"); return False


async def clear_content(card_id: str, client_key=None) -> bool:
    """Удаляет запись с контентом для карточки (по ключу клиента или общую)."""
    from models.CardContent import CardContent
    from sqlalchemy import select, delete
    from database.connection import session_factory
    try:
        async with session_factory() as session:
            q = select(CardContent).where(CardContent.card_id == _UUID(str(card_id)))
            if client_key is not None:
                q = q.where(CardContent.client_key == client_key)
            result = await session.execute(q)
            existing = result.scalar_one_or_none()
            if existing:
                # можно удалить запись
                await session.delete(existing)
                await session.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка очистки контента карточки {card_id}: {e}")
        return False


async def get_users(telegram_id=None, role=None, user_id=None, department=None) -> list[dict]:
    from models.User import User
    kwargs = {}
    if telegram_id is not None: kwargs["telegram_id"] = telegram_id
    if role is not None: kwargs["role"] = role
    if user_id is not None: kwargs["user_id"] = _UUID(str(user_id))
    if department is not None: kwargs["department"] = department
    users = await User.filter_by(**kwargs) if kwargs else await User.get_all()
    return [u.to_dict() for u in users]


async def get_user(telegram_id=None, role=None, user_id=None, department=None) -> dict | None:
    users = await get_users(telegram_id, role, user_id, department)
    return users[0] if users else None


async def get_user_role(telegram_id: int) -> str | None:
    user = await get_user(telegram_id=telegram_id)
    return user.get("role") if user else None


async def create_user(telegram_id: int, role: str, department=None, about=None, name=None) -> dict | None:
    from models.User import User
    try:
        existing = await User.get_by_key("telegram_id", telegram_id)
        if existing: return {"error": "User already exists"}
        user = await User.create(telegram_id=telegram_id, role=role, department=department, about=about, name=name, task_per_year=0, task_per_month=0, tasks=0, tasks_checked=0, tasks_created=0)
        return user.to_dict()
    except Exception as e:
        logger.error(f"Ошибка создания пользователя (telegram_id={telegram_id}): {e}"); return None


async def update_user(telegram_id: int, role=None, department=None, about=None, name=None) -> dict | None:
    from models.User import User
    try:
        user = await User.get_by_key("telegram_id", telegram_id)
        if not user: return None
        updates = {k: v for k, v in [("role", role), ("about", about), ("name", name)] if v is not None}
        if department is not None: updates["department"] = department.value if hasattr(department, "value") else department
        if updates: await user.update(**updates)
        return user.to_dict()
    except Exception as e:
        logger.error(f"Ошибка обновления пользователя (telegram_id={telegram_id}): {e}"); return None


async def delete_user(telegram_id: int) -> bool:
    from models.User import User
    try:
        user = await User.get_by_key("telegram_id", telegram_id)
        if user: await user.delete()
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления пользователя (telegram_id={telegram_id}): {e}"); return False


async def insert_scene(user_id: int, data: dict) -> bool:
    from models.Scene import Scene
    try:
        if await Scene.get_by_key("user_id", user_id): return False
        await Scene.create(user_id=user_id, scene=data.get("scene",""), scene_path=data.get("scene_path",""), page=data.get("page",""), message_id=data.get("message_id",0), data=data.get("data",{}))
        return True
    except Exception as e:
        logger.error(f"Ошибка создания сцены для пользователя {user_id}: {e}"); return False


async def load_scene(user_id: int) -> dict | None:
    from models.Scene import Scene
    scene = await Scene.get_by_key("user_id", user_id)
    return scene.to_dict() if scene else None


def _serialize_for_json(obj):
    """Рекурсивно конвертирует UUID и другие non-JSON объекты в строки"""
    if isinstance(obj, _UUID):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_serialize_for_json(item) for item in obj]
    elif hasattr(obj, '__dict__') and hasattr(obj, '__class__'):
        # Enums и другие custom objects
        return str(obj)
    return obj


async def update_scene(user_id: int, data: dict) -> bool:
    from models.Scene import Scene
    try:
        scene = await Scene.get_by_key("user_id", user_id)
        if not scene: return False
        updates = {k: data[k] for k in ("scene","scene_path","page","message_id","data") if k in data and data[k] is not None}
        
        # Сериализуем UUID и другие non-JSON объекты
        if "data" in updates:
            updates["data"] = _serialize_for_json(updates["data"])
        
        if updates: await scene.update(**updates)
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления сцены пользователя {user_id}: {e}"); return False


async def delete_scene(user_id: int) -> bool:
    from models.Scene import Scene
    try:
        scene = await Scene.get_by_key("user_id", user_id)
        if scene: await scene.delete()
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления сцены пользователя {user_id}: {e}"); return False


async def get_all_scenes() -> list[dict]:
    from models.Scene import Scene
    scenes = await Scene.get_all()
    return [s.to_dict() for s in scenes]


async def download_file(file_id: str) -> tuple[bytes | None, int | None]:
    from models.CardFile import CardFile
    from modules.storage import download_file as _dl
    try:
        cf = await CardFile.get_by_id(_UUID(str(file_id)))
        if not cf: return None, 404
        return await _dl(cf.filename)
    except Exception as e:
        logger.error(f"Ошибка скачивания файла {file_id}: {e}"); return None, 500


async def get_file_info(file_id: str) -> dict | None:
    from models.CardFile import CardFile
    try:
        cf = await CardFile.get_by_id(_UUID(str(file_id)))
        return cf.to_dict() if cf else None
    except Exception: return None


async def list_files(card_id: str) -> list[dict]:
    from models.CardFile import CardFile
    files = await CardFile.filter_by(card_id=_UUID(str(card_id)))
    return [f.to_dict() for f in sorted(files, key=lambda x: x.order)]


async def delete_file(file_id: str) -> bool:
    from models.CardFile import CardFile
    try:
        cf = await CardFile.get_by_id(_UUID(str(file_id)))
        if cf: await cf.delete()
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления файла {file_id}: {e}"); return False


async def upload_file(card_id: str, file_data: bytes, filename: str, content_type=None) -> dict | None:
    from modules.storage import upload_file as _up
    from models.CardFile import CardFile
    try:
        result = await _up(file_data, filename, content_type)
        if result.get("status") != "success": return None
        cf = await CardFile.create(card_id=_UUID(str(card_id)), filename=result["filename"], original_filename=filename, size=len(file_data), data_info={"content_type": content_type or ""}, order=0)
        return cf.to_dict()
    except Exception as e:
        logger.error(f"Ошибка загрузки файла {filename} к карточке {card_id}: {e}"); return None


async def upload_files_to_card(card_id: str, files: list[dict], bot) -> int:
    """Загружает список файлов (из Telegram) к карточке. Возвращает количество успешно загруженных файлов."""
    from modules.file_utils import download_telegram_file
    uploaded = 0
    for file_info in files:
        try:
            file_id = file_info.get('file_id')
            filename = file_info.get('name', 'file')
            if not file_id:
                continue
            file_data = await download_telegram_file(bot, file_id)
            if not file_data:
                continue
            result = await upload_file(card_id=card_id, file_data=file_data, filename=filename)
            if result:
                uploaded += 1
        except Exception as e:
            print(f"upload_files_to_card error for {file_info.get('name')}: {e}")
    return uploaded


async def add_entity(card_id: str, client_id: str, entity_type: str, data: dict, name=None) -> dict | None:
    from models.Entity import Entity
    try:
        entity = await Entity.create(card_id=_UUID(str(card_id)), client_key=client_id, data=data, type=entity_type)
        return entity.to_dict()
    except Exception as e:
        print(f"add_entity error: {e}"); return None


async def get_entities(card_id: str, client_id: str) -> list[dict] | None:
    from models.Entity import Entity
    entities = await Entity.filter_by(card_id=_UUID(str(card_id)), client_key=client_id)
    return [e.to_dict() for e in entities]



async def get_card_by_message_id(message_id: int) -> dict | None:
    from models.CardMessage import CardMessage
    from models.Card import Card
    try:
        messages = await CardMessage.filter_by(message_id=message_id)
        if not messages: return None
        card = await Card.get_by_key("card_id", messages[0].card_id)
        return card.to_dict() if card else None
    except Exception as e:
        print(f"get_card_by_message_id error: {e}"); return None


async def create_card(title: str, description: str = "", deadline=None, send_time=None,
                      channels: list = None, tags: list = None, need_check: bool = True,
                      executor_id=None, customer_id=None, editor_id=None,
                      image_prompt=None, type_id=None, **kwargs) -> dict | None:
    from models.Card import Card
    from models.ClientSetting import ClientSetting
    from modules.executors_client import send_forum_message
    from datetime import datetime
    try:
        card = await Card.create(
            name=title, description=description,
            task_id=kwargs.get("task_id", 0),
            clients=channels or [],
            tags=tags or [],
            deadline=datetime.fromisoformat(str(deadline)) if deadline else None,
            send_time=datetime.fromisoformat(str(send_time)) if send_time else None,
            image_prompt=image_prompt,
            customer_id=_UUID(str(customer_id)) if customer_id else None,
            executor_id=_UUID(str(executor_id)) if executor_id else None,
            need_check=need_check,
            editor_id=_UUID(str(editor_id)) if editor_id else None,
        )
        for key in channels or []:
            try:
                await ClientSetting.create(card_id=card.card_id, client_key=str(key), data={})
            except Exception: pass
        is_public = str(type_id) in ("public", "CardType.public", "1")
        if is_public:
            await send_forum_message(str(card.card_id))
        return card.to_dict()
    except Exception as e:
        print(f"create_card error: {e}"); return None


async def delete_card(card_id: str) -> dict:
    from models.Card import Card
    from models.CardFile import CardFile
    from models.CardMessage import CardMessage
    from modules.executors_client import delete_forum_message_by_id, delete_all_complete_previews
    from modules.calendar import delete_calendar_event
    try:
        card = await Card.get_by_id(_UUID(str(card_id)))
        if not card: return {"detail": "Card not found", "status": 404}
        files = await CardFile.filter_by(card_id=card.card_id)
        for f in files: await f.delete()
        messages = await CardMessage.filter_by(card_id=card.card_id)
        forum_msgs = [m for m in messages if m.message_type == "forum"]
        complete_msgs = [m for m in messages if "complete" in (m.message_type or "")]
        for msg in forum_msgs:
            await delete_forum_message_by_id(msg.message_id)
        await delete_all_complete_previews([m.message_id for m in complete_msgs if "info" in m.message_type])
        for msg in messages: await msg.delete()
        if card.calendar_id:
            try: await delete_calendar_event(card.calendar_id)
            except Exception: pass
        await card.delete()
        return {"detail": "Card deleted successfully", "status": 200}
    except Exception as e:
        print(f"delete_card error: {e}"); return {"detail": str(e), "status": 500}


async def send_now(card_id: str) -> dict:
    from models.Card import Card
    from global_modules.classes.enums import CardStatus
    from global_modules.timezone import now_naive as moscow_now
    from datetime import timedelta
    try:
        card = await Card.get_by_id(_UUID(str(card_id)))
        if not card: return {"detail": "Card not found", "status": 404}
        if card.status != CardStatus.ready:
            return {"detail": "Card must be in ready status", "status": 400}
        send_time = moscow_now() + timedelta(seconds=5)
        await card.update(send_time=send_time)
        return {"detail": "Card scheduled for immediate sending", "send_time": send_time.isoformat(), "status": 200}
    except Exception as e:
        print(f"send_now error: {e}"); return {"detail": str(e), "status": 500}


async def set_client_settings(card_id: str, client_id: str, setting_type: str, data: dict) -> dict:
    from models.Card import Card
    from models.ClientSetting import ClientSetting
    from sqlalchemy import select
    from database.connection import session_factory
    try:
        card = await Card.get_by_id(_UUID(str(card_id)))
        if not card: return {"detail": "Card not found", "status": 404}
        async with session_factory() as session:
            q = select(ClientSetting).where(
                ClientSetting.card_id == card.card_id,
                ClientSetting.client_key == client_id
            )
            result = await session.execute(q)
            setting = result.scalar_one_or_none()
            if setting:
                existing = setting.data or {}
                existing[setting_type] = data
                await setting.update(session=session, data=existing)
            else:
                session.add(ClientSetting(card_id=card.card_id, client_key=client_id, data={setting_type: data}))
            await session.commit()
        return {"detail": "Settings updated", "status": 200}
    except Exception as e:
        print(f"set_client_settings error: {e}"); return {"detail": str(e), "status": 500}


async def get_entity(entity_id: str) -> dict | None:
    from models.Entity import Entity
    ent = await Entity.get_by_id(_UUID(str(entity_id)))
    return ent.to_dict() if ent else None


async def update_entity(entity_id: str, data: dict) -> dict | None:
    from models.Entity import Entity
    from datetime import datetime
    try:
        ent = await Entity.get_by_id(_UUID(str(entity_id)))
        if not ent: return None
        updated = ent.data.copy() if ent.data else {}
        updated.update(data)
        updated["updated_at"] = datetime.now().isoformat()
        await ent.update(data=updated)
        return ent.to_dict()
    except Exception as e:
        print(f"update_entity error: {e}"); return None


async def delete_entity_by_id(entity_id: str) -> bool:
    from models.Entity import Entity
    try:
        ent = await Entity.get_by_id(_UUID(str(entity_id)))
        if ent: await ent.delete()
        return True
    except Exception as e:
        print(f"delete_entity error: {e}"); return False


async def get_busy_slots(start: str = None, end: str = None) -> list[dict]:
    from models.Card import Card
    from sqlalchemy import select
    from database.connection import session_factory
    from datetime import datetime
    try:
        async with session_factory() as session:
            stmt = select(Card.card_id, Card.send_time).where(Card.send_time != None)
            if start:
                stmt = stmt.where(Card.send_time >= datetime.fromisoformat(start))
            if end:
                stmt = stmt.where(Card.send_time <= datetime.fromisoformat(end))
            result = await session.execute(stmt)
            return [{"card_id": str(cid), "send_time": st.isoformat()} for cid, st in result.all() if st]
    except Exception as e:
        print(f"get_busy_slots error: {e}"); return []


async def notify_executor(card_id: str, message: str) -> bool:
    from models.Card import Card
    from models.User import User
    from modules import executor_bridge
    try:
        card = await Card.get_by_id(_UUID(str(card_id)))
        if not card or not card.executor_id: return False
        user = await User.get_by_id(card.executor_id)
        if not user: return False
        return await executor_bridge.notify_user(user.telegram_id, message)
    except Exception as e:
        print(f"notify_executor error: {e}"); return False


async def get_tags() -> list[dict]:
    from models.Tag import Tag
    tags = await Tag.get_all()
    return [{"id": t.id, "key": t.key, "name": t.name, "tag": t.tag,
             "forward_to_topic": t.forward_to_topic, "order": t.order} for t in sorted(tags, key=lambda x: x.order)]


async def create_tag(key: str, name: str, tag: str, forward_to_topic=None, order: int = 0) -> dict | None:
    from models.Tag import Tag
    try:
        existing = await Tag.get_by_key("key", key)
        if existing: return None
        t = await Tag.create(key=key, name=name, tag=tag, forward_to_topic=forward_to_topic, order=order)
        return {"id": t.id, "key": t.key, "name": t.name, "tag": t.tag,
                "forward_to_topic": t.forward_to_topic, "order": t.order}
    except Exception as e:
        print(f"create_tag error: {e}"); return None


async def update_tag(key: str, name=None, tag=None, forward_to_topic=None, order=None) -> dict | None:
    from models.Tag import Tag
    try:
        t = await Tag.get_by_key("key", key)
        if not t: return None
        updates = {k: v for k, v in [("name", name), ("tag", tag), ("forward_to_topic", forward_to_topic), ("order", order)] if v is not None}
        if updates: await t.update(**updates)
        return {"id": t.id, "key": t.key, "name": t.name, "tag": t.tag,
                "forward_to_topic": t.forward_to_topic, "order": t.order}
    except Exception as e:
        print(f"update_tag error: {e}"); return None


async def delete_tag(key: str) -> bool:
    from models.Tag import Tag
    try:
        t = await Tag.get_by_key("key", key)
        if t: await t.delete()
        return True
    except Exception as e:
        print(f"delete_tag error: {e}"); return False


# Обратная совместимость: brain_client.method() и module-level functions
class _BrainClientCompat:
    get_cards = staticmethod(get_cards)
    update_card = staticmethod(update_card)
    change_card_status = staticmethod(change_card_status)
    add_editor_note = staticmethod(add_editor_note)
    get_messages = staticmethod(get_messages)
    set_content = staticmethod(set_content)
    clear_content = staticmethod(clear_content)
    get_users = staticmethod(get_users)
    get_user = staticmethod(get_user)
    get_user_role = staticmethod(get_user_role)
    create_user = staticmethod(create_user)
    update_user = staticmethod(update_user)
    delete_user = staticmethod(delete_user)
    insert_scene = staticmethod(insert_scene)
    load_scene = staticmethod(load_scene)
    update_scene = staticmethod(update_scene)
    delete_scene = staticmethod(delete_scene)
    get_all_scenes = staticmethod(get_all_scenes)
    download_file = staticmethod(download_file)
    get_file_info = staticmethod(get_file_info)
    list_files = staticmethod(list_files)
    delete_file = staticmethod(delete_file)
    upload_file = staticmethod(upload_file)
    add_entity = staticmethod(add_entity)
    get_entities = staticmethod(get_entities)
    notify_executor = staticmethod(notify_executor)
    get_card_by_message_id = staticmethod(get_card_by_message_id)
    create_card = staticmethod(create_card)
    delete_card = staticmethod(delete_card)
    send_now = staticmethod(send_now)
    set_client_settings = staticmethod(set_client_settings)
    get_entity = staticmethod(get_entity)
    update_entity = staticmethod(update_entity)
    delete_entity_by_id = staticmethod(delete_entity_by_id)
    get_busy_slots = staticmethod(get_busy_slots)
    upload_files_to_card = staticmethod(upload_files_to_card)
    get_tags = staticmethod(get_tags)
    create_tag = staticmethod(create_tag)
    update_tag = staticmethod(update_tag)
    delete_tag = staticmethod(delete_tag)

brain_client = _BrainClientCompat()
