"""
Модуль обратной совместимости.
HTTP-клиенты между сервисами удалены (монолит).
Функции реэкспортируются из global_modules.brain_client.
"""
from modules.exec.brain_client import (
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
    download_file,
    get_file_info,
    list_files,
    delete_file,
    upload_file,
    add_entity,
    get_entities,
    notify_executor,
)

