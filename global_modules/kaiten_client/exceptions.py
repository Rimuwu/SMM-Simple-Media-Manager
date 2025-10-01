"""
Исключения для Kaiten API клиента.
"""


class KaitenApiError(Exception):
    """Базовое исключение для ошибок Kaiten API."""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data


class KaitenNotFoundError(KaitenApiError):
    """Ошибка 404 - ресурс не найден."""
    
    def __init__(self, message: str = "Resource not found", resource_id: str = None):
        super().__init__(message, status_code=404)
        self.resource_id = resource_id


class KaitenValidationError(KaitenApiError):
    """Ошибка валидации данных (422)."""
    
    def __init__(self, message: str = "Validation error", errors: dict = None):
        super().__init__(message, status_code=422)
        self.errors = errors or {}


class KaitenAuthenticationError(KaitenApiError):
    """Ошибка аутентификации (401)."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class KaitenPermissionError(KaitenApiError):
    """Ошибка доступа (403)."""
    
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status_code=403)


class KaitenRateLimitError(KaitenApiError):
    """Ошибка превышения лимита запросов (429)."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class KaitenServerError(KaitenApiError):
    """Ошибка сервера (5xx)."""
    
    def __init__(self, message: str = "Server error", status_code: int = 500):
        super().__init__(message, status_code=status_code)


class KaitenConnectionError(KaitenApiError):
    """Ошибка соединения с API."""
    
    def __init__(self, message: str = "Connection error"):
        super().__init__(message)


class KaitenTimeoutError(KaitenApiError):
    """Ошибка таймаута запроса."""
    
    def __init__(self, message: str = "Request timeout"):
        super().__init__(message)