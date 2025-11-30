from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from tg.oms.manager import scene_manager

router = APIRouter(prefix="/events", tags=["Events"])

class ExecutorChangeEvent(BaseModel):
    task_id: UUID
    new_executor_id: Optional[UUID] = None
    old_executor_id: Optional[UUID] = None

@router.post("/executor_changed")
async def executor_changed(event: ExecutorChangeEvent):
    """
    Обработчик события смены исполнителя.
    Ищет все активные сцены, связанные с этой задачей, уведомляет пользователей и закрывает сцены.
    """

    active_scenes = list(scene_manager._instances.values())
    count = 0

    for scene in active_scenes:
        # Check if the scene has a selected task
        scene_task_id_str = scene.data.get('scene', {}).get('selected_task')
        
        if not scene_task_id_str:
            continue

        # Compare UUIDs
        try:
            scene_task_id = UUID(str(scene_task_id_str))
        except ValueError:
            continue

        if scene_task_id == event.task_id:
            count += 1
            # Notify user
            try:
                await scene.bot.send_message(
                    chat_id=scene.user_id,
                    text="⚠️ Исполнитель задачи был изменен. Сцена завершена."
                )
            except Exception as e:
                print(f"Failed to send message to {scene.user_id}: {e}")

            # End scene
            await scene.end()

    return {"status": "ok", "processed_scenes": count}


@router.post("/close_scene/{user_id}")
async def close_scene(user_id: int):
    """
    Закрывает все активные сцены для указанного пользователя.
    """
    active_scenes = list(scene_manager._instances.values())

    for scene in active_scenes:
        if scene.user_id == user_id:
            await scene.end()

    return {"status": "ok", "closed_scenes": len([s for s in active_scenes if s.user_id == user_id])}


class UpdateScenesEvent(BaseModel):
    scene_name: Optional[str] = None
    page_name: Optional[str] = None
    data_key: Optional[str] = None
    data_value: Optional[str] = None


@router.post("/update_scenes")
async def update_scenes(event: UpdateScenesEvent):
    """
    Обновляет (перезагружает) все активные сцены, соответствующие указанным критериям.
    
    Параметры:
    - scene_name: название сцены (например, 'user-task')
    - page_name: название текущей страницы (например, 'main-page')
    - data_key: ключ в данных сцены для проверки (например, 'task_id')
    - data_value: значение для проверки (например, UUID карточки)
    
    Пример использования:
    Обновить все сцены редактирования задачи с task_id = "123e4567-e89b-12d3-a456-426614174000"
    """
    active_scenes = list(scene_manager._instances.values())
    updated_count = 0
    
    for scene in active_scenes:
        # Проверяем соответствие критериям
        match = True
        
        # Проверка названия сцены
        if event.scene_name and scene.__scene_name__ != event.scene_name:
            match = False
        
        # Проверка текущей страницы
        if event.page_name and scene.current_page != event.page_name:
            match = False
        
        # Проверка данных
        if event.data_key and event.data_value:
            scene_value = scene.data.get('scene', {}).get(event.data_key)
            # Приводим к строке для сравнения
            if str(scene_value) != str(event.data_value):
                match = False
        
        # Если все критерии совпадают - обновляем сцену
        if match:
            try:
                await scene.update_message()
                updated_count += 1
            except Exception as e:
                print(f"Failed to update scene for user {scene.user_id}: {e}")
    
    return {
        "status": "ok",
        "total_active_scenes": len(active_scenes),
        "updated_scenes": updated_count
    }