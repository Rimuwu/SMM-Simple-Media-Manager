from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.User import User
from modules.api_client import executors_api
from modules.logs import brain_logger as logger

router = APIRouter(prefix='/user')

@router.get("/get")
async def get(
        telegram_id: Optional[int] = None,
        tasker_id: Optional[int] = None,
        role: Optional[str] = None,
        user_id = None,
        department: Optional[str] = None
    ):
    query = {
        'telegram_id': telegram_id,
        'tasker_id': tasker_id,
        'role': role,
        'user_id': user_id,
        'department': department
    }

    # Удаляем None значения из запроса
    query = {k: v for k, v in query.items() if v is not None}
    users = await User.filter_by(**query)
    if not users:
        raise HTTPException(
            status_code=404, detail="User not found")

    return [user.to_dict() for user in users]

class UserCreate(BaseModel):
    telegram_id: int
    role: str
    tasker_id: Optional[int] = None
    department: Optional[str] = None
    about: Optional[str] = None

@router.post("/create")
async def create(user_data: UserCreate):
    try:
        existing_user = await User.get_by_key('telegram_id', user_data.telegram_id)
        if existing_user:
            logger.warning(f"Попытка создания существующего пользователя: {user_data.telegram_id}")
            return {'error': 'User with this telegram_id already exists'}

        user = await User.create(
            telegram_id=user_data.telegram_id,
            role=user_data.role,
            tasker_id=user_data.tasker_id,
            department=user_data.department,
            about=user_data.about,
            task_per_year=0,
            task_per_month=0,
            tasks=0
        )
        logger.info(f"Создан новый пользователь: {user.telegram_id}, роль: {user.role}")
        return user.to_dict()

    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

class UserUpdate(BaseModel):
    telegram_id: int
    role: Optional[str] = None
    tasker_id: Optional[int] = None
    department: Optional[str] = None
    about: Optional[str] = None

@router.post("/update")
async def update(user_data: UserUpdate):
    user = await User.get_by_key(
        'telegram_id', user_data.telegram_id
        )

    if not user:
        logger.warning(f"Попытка обновления несуществующего пользователя: {user_data.telegram_id}")
        return {'error': 'User not found'}

    update_data = {}
    if user_data.role is not None:
        if user_data.role != user.role:
            logger.info(f"Изменение роли пользователя {user.telegram_id}: {user.role} -> {user_data.role}")
            await executors_api.post(
                '/events/close_scene/' + str(user.telegram_id)
            )

        update_data['role'] = user_data.role

    if user_data.tasker_id is not None:
        update_data['tasker_id'] = user_data.tasker_id

    if user_data.department is not None:
        update_data['department'] = user_data.department

    if user_data.about is not None:
        update_data['about'] = user_data.about

    try:
            await user.update(**update_data)
            logger.info(f"Пользователь {user.telegram_id} обновлен: {update_data}")
            return user.to_dict()
    except Exception as e:
        logger.error(f"Ошибка при обновлении пользователя {user.telegram_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    except Exception as e:
        print(f"Error in user.update: {e}")
        raise HTTPException(status_code=500, 
                            detail=f"Internal server error: {str(e)}")

@router.delete("/delete")
async def delete(telegram_id: int):
    user = await User.get_by_key('telegram_id', telegram_id)
    if not user:
        raise HTTPException(status_code=404, 
                            detail="User not found")

    await executors_api.post(
            '/events/close_scene/' + str(user.telegram_id)
        )

    await user.delete()
    return {"status": "ok"}