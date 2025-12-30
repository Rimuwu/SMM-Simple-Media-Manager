from fastapi import APIRouter, Request, BackgroundTasks
from pydantic import BaseModel
from modules.ai import send
from global_modules.limiter import limiter
from typing import Optional, Dict, Any
from modules.api_client import executors_api
import asyncio
import json

router = APIRouter(prefix="/ai")

# Модель данных для создания карты
class AiRequest(BaseModel):
    prompt: str
    # callback: {'user_id': int, 'scene': str, 'page': str, 'function': str}
    callback: Optional[Dict[str, Any]] = None

async def _process_and_callback(prompt: str, callback: Optional[Dict[str, Any]] = None):
    """Производит обработку (в отдельном потоке, если send блокирующий) и POST-ит результат в executors."""
    try:
        # Выполняем send в фоновом потоке (на случай блокирующей реализации)
        response = await asyncio.to_thread(send, prompt)

        # Приводим ответ к строке
        if isinstance(response, str):
            result = response
        else:
            result = json.dumps(response, ensure_ascii=False)

        # Формируем payload для callback
        payload = {}
        if callback and isinstance(callback, dict):
            payload.update(callback)
        payload["result"] = result

        # Отправляем результат в executors
        resp, status = await executors_api.post('/events/ai_callback', data=payload)
        if status != 200:
            print(f"AI callback post failed: status={status} resp={resp}")
    except Exception as e:
        print(f"Error in background AI processing: {e}")

@router.post("/send")
@limiter.limit("5/minute")
async def ai(request: Request, data: AiRequest, background_tasks: BackgroundTasks):
    """Принимает prompt и опциональный callback, возвращает мгновенно подтверждение и обрабатывает в фоне."""
    # Запускаем обработку в фоне
    background_tasks.add_task(_process_and_callback, data.prompt, data.callback)

    return {"status": "accepted"}