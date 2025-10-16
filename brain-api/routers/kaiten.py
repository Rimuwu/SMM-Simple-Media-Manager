from fastapi import APIRouter
from modules.kaiten import kaiten

router = APIRouter(prefix='/kaiten')

@router.get("/get-users")
async def get_users(only_virtual: int = 0):
    async with kaiten as k:
        try:
            users = await k.get_company_users(only_virtual=bool(only_virtual))
        except TypeError:
            users = await k.get_company_users()
            if only_virtual:
                users = [
                    u for u in users
                    if u.get("is_virtual") or u.get("virtual") or u.get("isVirtual")
                ]
        return users