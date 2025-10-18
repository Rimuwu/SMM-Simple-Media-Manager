from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.User import User

router = APIRouter(prefix='/user')

@router.get("/get")
async def get(
        telegram_id: Optional[int] = None,
        tasker_id: Optional[int] = None,
        role: Optional[str] = None
    ):
    query = {
        'telegram_id': telegram_id,
        'tasker_id': tasker_id,
        'role': role
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
            tasker_id=user_data.tasker_id
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
        update_data['role'] = user_data.role
    if user_data.tasker_id is not None:
        update_data['tasker_id'] = user_data.tasker_id

    try:
        await user.update(**update_data)
        return user.to_dict()
    except Exception as e:
        print(f"Error in user.update: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")