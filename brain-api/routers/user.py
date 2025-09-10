from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.User import User, UserRole
from services.user_service import UserService

router = APIRouter(prefix="/user", tags=["user"])

class UserCreate(BaseModel):
    telegram_id: int
    tasker_id: str | None = None
    role: UserRole = UserRole.copywriter

class UserResponse(BaseModel):
    user_id: str
    telegram_id: int
    tasker_id: str | None
    role: UserRole

@router.post("/create", response_model=UserResponse)
async def create_user(user_data: UserCreate):
    """Создать нового пользователя"""
    # Проверяем, не существует ли уже пользователь
    if await UserService.user_exists(user_data.telegram_id):
        raise HTTPException(status_code=400, 
                            detail="User already exists")

    user = await UserService.create_user(
        telegram_id=user_data.telegram_id,
        role=user_data.role,
        tasker_id=user_data.tasker_id
    )

    return UserResponse(
        user_id=str(user.user_id),
        telegram_id=user.telegram_id,
        tasker_id=user.tasker_id,
        role=user.role
    )

@router.get("/telegram/{telegram_id}", response_model=UserResponse)
async def get_user_by_telegram_id(telegram_id: int):
    """Получить пользователя по telegram_id"""
    user = await UserService.get_user_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, 
                            detail="User not found")

    return UserResponse(
        user_id=str(user.user_id),
        telegram_id=user.telegram_id,
        tasker_id=user.tasker_id,
        role=user.role
    )

@router.get("/all")
async def get_user_by_telegram_id():
    users = await UserService.get_all_users()
    return {"users": users}