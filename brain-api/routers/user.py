from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.User import User
from modules.api_client import executors_api

router = APIRouter(prefix='/user')

@router.get("/get")
async def get(
        telegram_id: Optional[int] = None,
        tasker_id: Optional[int] = None,
        role: Optional[str] = None,
        user_id = None
    ):
    query = {
        'telegram_id': telegram_id,
        'tasker_id': tasker_id,
        'role': role,
        'user_id': user_id
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

@router.post("/create")
async def create(user_data: UserCreate):
    try:
        existing_user = await User.get_by_key('telegram_id', user_data.telegram_id)
        if existing_user:
            return {'error': 'User with this telegram_id already exists'}

        user = await User.create(
            telegram_id=user_data.telegram_id,
            role=user_data.role,
            tasker_id=user_data.tasker_id,
            task_per_year=0,
            task_per_month=0,
            tasks=0
        )
        return user.to_dict()

    except Exception as e:
        print(f"Error in user.create: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

class UserUpdate(BaseModel):
    telegram_id: int
    role: Optional[str] = None
    tasker_id: Optional[int] = None

@router.post("/update")
async def update(user_data: UserUpdate):
    user = await User.get_by_key(
        'telegram_id', user_data.telegram_id
        )

    if not user:
        return {'error': 'User not found'}

    update_data = {}
    if user_data.role is not None:
        if user_data.role != user.role:
            await executors_api.post(
                '/events/close_scene/' + str(user.telegram_id)
            )

        update_data['role'] = user_data.role

    if user_data.tasker_id is not None:
        update_data['tasker_id'] = user_data.tasker_id

    try:
        await user.update(**update_data)
        return user.to_dict()
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