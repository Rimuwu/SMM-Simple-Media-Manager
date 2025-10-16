from global_modules.api_client import APIClient

brain_api = APIClient('http://brain:8000')

async def get_user_role(telegram_id: int) -> str | None:
    """Получить роль пользователя по telegram_id"""
    user, status_code = await brain_api.get(f"/user/telegram/{telegram_id}")
    if status_code == 200 and user:
        return user.role
    return None