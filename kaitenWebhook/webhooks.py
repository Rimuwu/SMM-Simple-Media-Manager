"""
Kaiten External Webhooks Server

Простой сервер для обработки webhook уведомлений от Kaiten.
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class WebhookEvent:
    """Структура webhook события."""
    event: str
    author: Dict[str, Any]
    data: Dict[str, Any]
    timestamp: datetime

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> 'WebhookEvent':
        """Создает событие из webhook payload."""
        return cls(
            event=payload.get('event', ''),
            author=payload.get('data', {}).get('author', {}),
            data=payload.get('data', {}),
            timestamp=datetime.now()
        )


class WebhookProcessor:
    """Процессор для обработки webhook событий."""
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._global_handlers: List[Callable] = []

    def register_handler(self, event_type: str, handler: Callable):
        """Регистрирует обработчик для конкретного типа события."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.info(f"Зарегистрирован обработчик для события: {event_type}")

    def register_global_handler(self, handler: Callable):
        """Регистрирует глобальный обработчик для всех событий."""
        self._global_handlers.append(handler)
        logger.info("Зарегистрирован глобальный обработчик")

    async def process_event(self, event: WebhookEvent):
        """Обрабатывает событие, вызывая соответствующие обработчики."""
        logger.info(f"Обработка события: {event.event} от {event.author.get('name', 'Unknown')}")

        # Вызываем специфичные обработчики
        handlers = self._handlers.get(event.event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Ошибка в обработчике {handler.__name__}: {e}")

        # Вызываем глобальные обработчики
        for handler in self._global_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Ошибка в глобальном обработчике {handler.__name__}: {e}")


class KaitenWebhookServer:
    """Сервер для обработки webhook'ов от Kaiten."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080, webhook_path: str = "/kaiten/webhook"):
        self.host = host
        self.port = port
        self.webhook_path = webhook_path
        self.app = FastAPI(title="Kaiten Webhook Server", version="1.0.0")
        self.processor = WebhookProcessor()
        self._setup_routes()

    def _setup_routes(self):
        """Настраивает маршруты FastAPI."""

        @self.app.get("/")
        async def root():
            return {"message": "Kaiten Webhook Server", "status": "running"}

        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}

        @self.app.post(self.webhook_path)
        async def webhook_handler(request: Request, background_tasks: BackgroundTasks):
            try:
                payload = await request.json()
                logger.info(f"Получен webhook: {payload.get('event', 'unknown')}")

                event = WebhookEvent.from_payload(payload)
                background_tasks.add_task(self.processor.process_event, event)

                return JSONResponse(
                    status_code=200,
                    content={"message": "Webhook processed successfully"}
                )

            except json.JSONDecodeError:
                logger.error("Некорректный JSON в webhook payload")
                raise HTTPException(status_code=400, detail="Invalid JSON")
            except Exception as e:
                logger.error(f"Ошибка обработки webhook: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")

    def on(self, event_type: str):
        """Декоратор для регистрации обработчиков событий."""
        def decorator(func: Callable):
            self.processor.register_handler(event_type, func)
            return func
        return decorator

    def on_any(self):
        """Декоратор для регистрации глобального обработчика."""
        def decorator(func: Callable):
            self.processor.register_global_handler(func)
            return func
        return decorator

    def register_handler(self, event_type: str, handler: Callable):
        """Регистрирует обработчик программно."""
        self.processor.register_handler(event_type, handler)

    def register_global_handler(self, handler: Callable):
        """Регистрирует глобальный обработчик программно."""
        self.processor.register_global_handler(handler)

    def run(self, **kwargs):
        """Запускает сервер."""
        config_kwargs = {
            "host": self.host,
            "port": self.port,
            "log_level": "info"
        }
        config_kwargs.update(kwargs)

        logger.info(f"Запуск Kaiten Webhook Server на {self.host}:{self.port}")
        logger.info(f"Webhook endpoint: {self.webhook_path}")

        uvicorn.run(self.app, **config_kwargs)