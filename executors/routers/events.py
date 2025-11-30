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