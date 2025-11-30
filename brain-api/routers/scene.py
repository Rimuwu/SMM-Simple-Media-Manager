from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.Scene import Scene

router = APIRouter(prefix='/scene')


@router.get("/get/{user_id}")
async def get_scene(user_id: int):
    """Получение сцены пользователя"""
    scene = await Scene.get_by_key('user_id', user_id)
    
    if not scene:
        return None
    
    return scene.to_dict()

@router.get("/get-all")
async def get_all_scenes():
    """Получение всех сцен"""
    scenes = await Scene.get_all()
    
    if not scenes:
        return []
    
    return [scene.to_dict() for scene in scenes]

class SceneCreate(BaseModel):
    user_id: int
    scene: str
    scene_path: str
    page: str
    message_id: int
    data: dict


@router.post("/create")
async def create_scene(scene_data: SceneCreate):
    """Создание новой сцены"""
    try:
        # Проверяем, есть ли уже сцена для этого пользователя
        existing_scene = await Scene.get_by_key('user_id', scene_data.user_id)
        if existing_scene:
            return {'error': 'Scene for this user already exists'}

        # Создаем новую сцену
        scene = await Scene.create(
            user_id=scene_data.user_id,
            scene=scene_data.scene,
            scene_path=scene_data.scene_path,
            page=scene_data.page,
            message_id=scene_data.message_id,
            data=scene_data.data
        )
        
        return scene.to_dict()

    except Exception as e:
        print(f"Error in scene.create: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class SceneUpdate(BaseModel):
    user_id: int
    scene: Optional[str] = None
    scene_path: Optional[str] = None
    page: Optional[str] = None
    message_id: Optional[int] = None
    data: Optional[dict] = None


@router.post("/update")
async def update_scene(scene_data: SceneUpdate):
    """Обновление существующей сцены"""
    scene = await Scene.get_by_key('user_id', scene_data.user_id)

    if not scene:
        return {'error': 'Scene not found'}

    # Подготавливаем данные для обновления
    update_data = {}
    if scene_data.scene is not None:
        update_data['scene'] = scene_data.scene
    if scene_data.scene_path is not None:
        update_data['scene_path'] = scene_data.scene_path
    if scene_data.page is not None:
        update_data['page'] = scene_data.page
    if scene_data.message_id is not None:
        update_data['message_id'] = scene_data.message_id
    if scene_data.data is not None:
        update_data['data'] = scene_data.data

    try:
        await scene.update(**update_data)
        return scene.to_dict()
    except Exception as e:
        print(f"Error in scene.update: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/delete/{user_id}")
async def delete_scene(user_id: int):
    """Удаление сцены пользователя"""
    scene = await Scene.get_by_key('user_id', user_id)
    print(scene.__dict__.keys())

    if not scene:
        return {'error': 'Scene not found'}

    try:
        await scene.delete()
        return {
            'success': True, 
            'message': 'Scene deleted successfully'
            }
    except Exception as e:
        print(f"Error in scene.delete: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
