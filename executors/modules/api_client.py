"""
Модуль обратной совместимости.
Все функции перенесены в global_modules/brain_client.py

Этот файл сохранён для обратной совместимости импортов.
"""
from global_modules.api_client import APIClient
from global_modules.brain_client import (
    brain_client,
    get_cards,
    update_card,
    get_users,
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
)

# Для обратной совместимости - brain_api теперь это brain_client.api
brain_api = brain_client.api