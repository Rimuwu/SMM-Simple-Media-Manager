from typing import Optional
from fastapi import APIRouter, HTTPException
from models.User import User

router = APIRouter(prefix='/user')

@router.get("/get")
async def get(
        telegram_id: Optional[int] = None,
        tasker_id: Optional[int] = None,
    ):
    try:
        if telegram_id is not None:
            user = await User.get_by_key('telegram_id', telegram_id)
            return [user.to_dict()] if user else {'error': 'User not found'}
        elif tasker_id is not None:
            user = await User.get_by_key('tasker_id', tasker_id)
            return [user.to_dict()] if user else {'error': 'User not found'}
        else:
            users = await User.all()
            users_list = [u.to_dict() for u in users]
            return users_list
    except Exception as e:
        print(f"Error in user.get: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
