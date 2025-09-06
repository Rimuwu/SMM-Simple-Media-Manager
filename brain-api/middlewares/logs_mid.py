import time
from datetime import datetime
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from global_modules.logs import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            
            # Получаем информацию о клиенте
            client_ip = request.client.host if request.client else "unknown"
            client_port = request.client.port if request.client else "unknown"
            client_info = f"{client_ip}:{client_port}"
            
            # Формируем протокол
            protocol_version = f"HTTP/{request.scope.get('http_version', '1.1')}"

            # Логируем в стиле uvicorn
            logger.info(
                f"{client_info} - "
                f"\"{request.method} {request.url.path}{('?' + str(request.url.query)) if request.url.query else ''} {protocol_version}\" "
                f"{response.status_code}"
            )
            
            return response
            
        except Exception as e:
            # Логируем ошибку
            duration_ms = (time.perf_counter() - start_time) * 1000
            current_time = datetime.now().strftime("%H:%M:%S")
            client_ip = request.client.host if request.client else "unknown"
            
            logger.error(
                f"{current_time} ERROR:    {client_ip} - "
                f"Error in {request.method} {request.url.path} - "
                f"Duration: {duration_ms:.0f}ms - "
                f"Error: {str(e)}"
            )
            raise