from fastapi import APIRouter
from models.User import User

router = APIRouter(prefix='/user')

@router.post("/get")
async def get():
    users = await User.all()
    users_list = [u.to_dict() for u in users]

    return users_list
