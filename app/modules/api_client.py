"""
Модуль обратной совместимости.
HTTP-клиенты между сервисами удалены (монолит).
Функции реэкспортируются из global_modules.brain_client.
"""
from global_modules.brain_client import (
    brain_client,
    get_cards,
    update_card,
    get_users,
    get_user,
    get_user_role,
    create_user,
    update_user,
    delete_user,
    insert_scene,
    load_scene,
    update_scene,
    delete_scene,
    get_all_scenes,
    add_editor_note,
    get_kaiten_users,
    get_kaiten_users_dict,
    get_kaiten_files,
    download_file,
    get_file_info,
    list_files,
    delete_file,
    upload_file,
    add_entity,
    get_entities,
    notify_executor,
)


class _ExecutorsApiStub:
    """
    Stub-объект для обратной совместимости brain-модулей.
    Маршрутизирует вызовы executors_api.post(endpoint, data) к executor_bridge.
    """

    async def post(self, endpoint, data: dict = None, **kwargs):
        from modules import executor_bridge
        data = data or {}
        ep = str(endpoint)

        if "/forum/send-message-to-forum" in ep:
            return await executor_bridge.send_forum_message(data.get("card_id")), 200

        if "/forum/update-forum-message" in ep:
            return await executor_bridge.update_forum_message(data.get("card_id")), 200

        if "/forum/delete-forum-message-for-id" in ep:
            msg_id = ep.split("/")[-1] if ep.endswith(ep.split("/")[-1]) else data.get("message_id")
            return await executor_bridge.delete_forum_message_by_id(msg_id), 200

        if "/forum/delete-forum-message" in ep:
            return await executor_bridge.delete_forum_message(data.get("card_id")), 200

        if "/forum/send-complete-preview" in ep:
            return await executor_bridge.send_complete_preview(
                data.get("card_id"), data.get("client_key"),
                post_ids=data.get("post_ids"), info_id=data.get("info_id"),
                entities=data.get("entities")
            ), 200

        if "/forum/update-complete-preview" in ep:
            return await executor_bridge.update_complete_preview(
                data.get("card_id"), data.get("client_key"),
                post_ids=data.get("post_ids"), info_id=data.get("info_id"),
                entities=data.get("entities")
            ), 200

        if "/forum/delete-complete-preview" in ep:
            return await executor_bridge.delete_complete_preview(
                info_ids=data.get("info_ids"), post_ids=data.get("post_ids"),
                entities=data.get("entities")
            ), 200

        if "/forum/forward-first-by-tags" in ep:
            return await executor_bridge.send_post(data), 200

        if "/events/notify_user" in ep:
            return await executor_bridge.notify_user(data.get("user_id"), data.get("message")), 200

        if "/events/send_leaderboard" in ep:
            return await executor_bridge.send_leaderboard(data), 200

        if "/events/update_scenes" in ep:
            return await executor_bridge.update_scenes(**data), 200

        raise NotImplementedError(f"executors_api stub: unknown endpoint {ep!r}")


executors_api = _ExecutorsApiStub()


class _BrainApiStub:
    """
    Stub-объект для обратной совместимости executor-модулей.
    Маршрутизирует brain_api.get/post/delete(endpoint, ...) к brain_client функциям.
    """
    from urllib.parse import urlparse, parse_qs

    async def get(self, endpoint: str, params: dict = None, **kwargs):
        from urllib.parse import urlparse, parse_qs
        from global_modules import brain_client as bc
        params = params or {}
        ep = str(endpoint)

        # /card/get
        if ep.startswith('/card/get') and 'entities' not in ep and 'entity' not in ep and 'message' not in ep:
            cards = await bc.get_cards(**params)
            if not cards: return None, 404
            return cards, 200

        # /user/get
        if '/user/get' in ep:
            users = await bc.get_users(**params)
            user = users[0] if users else None
            return user, (200 if user else 404)

        # /time/busy-slots
        if '/time/busy-slots' in ep:
            start = params.get('start')
            end = params.get('end')
            slots = await bc.get_busy_slots(start=start, end=end)
            return {'busy_slots': slots}, 200

        # /card/entities?card_id=...&client_id=...
        if '/card/entities' in ep:
            parsed = urlparse(ep)
            qs = parse_qs(parsed.query)
            card_id = qs.get('card_id', [None])[0] or params.get('card_id')
            client_id = qs.get('client_id', [None])[0] or params.get('client_id')
            entities = await bc.get_entities(card_id, client_id) if card_id else []
            return {'entities': entities or []}, 200

        # /card/entity?card_id=...&client_id=...&entity_id=...
        if '/card/entity' in ep and '/entities' not in ep:
            parsed = urlparse(ep)
            qs = parse_qs(parsed.query)
            entity_id = qs.get('entity_id', [None])[0] or params.get('entity_id')
            ent = await bc.get_entity(entity_id) if entity_id else None
            return ent, (200 if ent else 404)

        # /card/get-card-by-message_id/{message_id}
        if '/get-card-by-message_id/' in ep:
            msg_id = int(ep.split('/')[-1])
            card = await bc.get_card_by_message_id(msg_id)
            return card, (200 if card else 404)

        raise NotImplementedError(f"brain_api GET stub: unknown endpoint {ep!r}")

    async def post(self, endpoint: str, data: dict = None, **kwargs):
        from global_modules import brain_client as bc
        data = data or {}
        ep = str(endpoint)

        # /card/create
        if '/card/create' in ep:
            result = await bc.create_card(
                title=data.get('title', ''), description=data.get('description', ''),
                deadline=data.get('deadline'), send_time=data.get('send_time'),
                channels=data.get('channels'), tags=data.get('tags'),
                need_check=data.get('need_check', True),
                executor_id=data.get('executor_id'), customer_id=data.get('customer_id'),
                editor_id=data.get('editor_id'), image_prompt=data.get('image_prompt'),
                type_id=data.get('type_id'),
            )
            return result, (200 if result else 500)

        # /card/add-entity
        if '/card/add-entity' in ep:
            result = await bc.add_entity(
                card_id=data.get('card_id'), client_id=data.get('client_id'),
                entity_type=data.get('entity_type'), data=data.get('data', {}),
                name=data.get('name')
            )
            return {'entity': result}, (200 if result else 500)

        # /card/update-entity
        if '/card/update-entity' in ep:
            result = await bc.update_entity(entity_id=data.get('entity_id'), data=data.get('data', {}))
            return {'entity': result}, (200 if result else 404)

        # /card/delete-entity
        if '/card/delete-entity' in ep:
            ok = await bc.delete_entity_by_id(data.get('entity_id'))
            return {'detail': 'deleted'}, (200 if ok else 500)

        # /card/clear-content
        if '/card/clear-content' in ep:
            ok = await bc.clear_content(data.get('card_id'), data.get('client_key'))
            return {'success': ok}, (200 if ok else 500)

        # /card/add-comment
        if '/card/add-comment' in ep:
            note = await bc.add_editor_note(
                card_id=data.get('card_id'), content=data.get('content', ''),
                author_user_id=data.get('author', '')
            )
            return {'note': note}, (200 if note else 500)

        # /card/send-now
        if '/card/send-now' in ep:
            result = await bc.send_now(data.get('card_id'))
            status = result.pop('status', 200) if result else 500
            return result, status

        # /card/set-client_settings
        if '/card/set-client_settings' in ep or '/card/set-client-settings' in ep:
            result = await bc.set_client_settings(
                card_id=data.get('card_id'), client_id=data.get('client_id'),
                setting_type=data.get('setting_type'), data=data.get('data', {})
            )
            status = result.pop('status', 200) if result else 500
            return result, status

        # /ai/send
        if '/ai/send' in ep:
            from modules import ai as ai_module
            result = await ai_module.send(data)
            return result, 200

        raise NotImplementedError(f"brain_api POST stub: unknown endpoint {ep!r}")

    async def delete(self, endpoint: str, **kwargs):
        from global_modules import brain_client as bc
        ep = str(endpoint)

        # /card/delete/{card_id}
        if '/card/delete/' in ep:
            card_id = ep.split('/card/delete/')[-1].strip('/')
            result = await bc.delete_card(card_id)
            status = result.pop('status', 200) if isinstance(result, dict) else 200
            return result, status

        raise NotImplementedError(f"brain_api DELETE stub: unknown endpoint {ep!r}")


brain_api = _BrainApiStub()
