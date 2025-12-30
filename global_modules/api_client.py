import aiohttp
import asyncio
import hashlib
import json
import time
from typing import Optional
from os import getenv


CACHE_TIMEOUT = 60

class APIClient:

    def __init__(self, base_url: str, *, timeout: Optional[aiohttp.ClientTimeout] = None, 
                 max_concurrency: int = 10, connector_limit: Optional[int] = None):
        """Инициализирует клиент с одной общей ClientSession, таймаутом и семафором для ограничения concurrency.

        timeout: по умолчанию aiohttp.ClientTimeout(total=90, connect=10, sock_read=90)
        max_concurrency: максимальное число параллельных запросов
        connector_limit: ограничение соединений для TCPConnector (None -> дефолт)
        """
        self.base_url = base_url
        self._cache = {}  # Внутренний кеш для хранения ответов
        self.CACHE_TIMEOUT = CACHE_TIMEOUT

        # Настройки timeout и отложенное создание коннектора/сессии
        self._timeout = timeout or aiohttp.ClientTimeout(total=90, connect=10, sock_read=90)
        # Сохраняем лимит коннектора, но не создаём его до появления event loop
        self._connector_limit = connector_limit
        self.session = None  # Будет создана лениво в async-контексте

        # Семафор для ограничения одновременных запросов
        self._semaphore = asyncio.BoundedSemaphore(max_concurrency)

        # Флаг закрытия сессии
        self._closed = False

    async def _ensure_session(self):
        """Лениво создаёт ClientSession и TCPConnector внутри запущенного event loop."""
        if self.session is None or getattr(self.session, "closed", False):
            connector = aiohttp.TCPConnector(limit=self._connector_limit) if self._connector_limit is not None else aiohttp.TCPConnector()
            self.session = aiohttp.ClientSession(timeout=self._timeout, connector=connector)
            self._closed = False

    def _generate_cache_key(self, method: str, endpoint: str, 
                            params: dict = None, data: dict = None) -> str:
        """Генерирует уникальный ключ кеша для запроса"""
        key_data = {
            'method': method,
            'endpoint': endpoint,
            'params': params,
            'data': data
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _is_cache_valid(self, cache_entry: dict) -> bool:
        """Проверяет, действителен ли кеш"""
        return time.time() - cache_entry['timestamp'] < self.CACHE_TIMEOUT

    def _get_from_cache(self, cache_key: str):
        """Получает данные из кеша, если они действительны"""
        if cache_key in self._cache:
            cache_entry = self._cache[cache_key]
            if self._is_cache_valid(cache_entry):
                return cache_entry['response'], cache_entry['status']
        return None, None

    def _save_to_cache(self, cache_key: str, response_data, status_code: int):
        """Сохраняет ответ в кеш"""
        self._cache[cache_key] = {
            'response': response_data,
            'status': status_code,
            'timestamp': time.time()
        }

    async def get(self, endpoint: str, 
                  params: dict = None,
                  use_cache: bool = False,
                  return_bytes: bool = False,
                  timeout: Optional[aiohttp.ClientTimeout] = None):
        # Убедимся, что сессия создана внутри event loop
        await self._ensure_session()
        # Фильтруем None значения из params
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        
        # Генерируем ключ кеша для GET запроса
        cache_key = self._generate_cache_key('GET', endpoint, params=params)

        if params:
            params = json.loads(json.dumps(params))  # Преобразуем параметры в стандартный формат

        if use_cache and not return_bytes:
            # Проверяем кеш (только для JSON ответов)
            cached_response, cached_status = self._get_from_cache(cache_key)
            if cached_response is not None:
                if getenv("DEBUG", False) == 'true':
                    print(f"Returning cached response for GET {endpoint}")
                return cached_response, cached_status

        # Выполняем запрос через общую сессию с семафором и таймаутом
        try:
            async with self._semaphore:
                async with self.session.get(f"{self.base_url}{endpoint}", params=params, timeout=timeout or self._timeout) as response:
                    status_code = response.status

                    if return_bytes:
                        # Возвращаем бинарные данные
                        response_data = await response.read()
                    else:
                        # Пытаемся распарсить JSON, но на случай текстовых ответов используем fallback
                        try:
                            response_data = await response.json()
                        except Exception:
                            response_data = await response.text()

                        # Кешируем только успешные JSON ответы (статус 200-299)
                        if 200 <= status_code < 300 and use_cache and not return_bytes:
                            self._save_to_cache(cache_key, response_data, status_code)

                    return response_data, status_code
        except asyncio.TimeoutError:
            if getenv("DEBUG", False) == 'true':
                print(f"GET timeout for {endpoint}")
            return {}, 504
        except aiohttp.ClientError as e:
            if getenv("DEBUG", False) == 'true':
                print(f"GET client error for {endpoint}: {e}")
            return {"error": str(e)}, 502

    async def post(self, endpoint: str, data: dict = None, no_filter_none: bool = False, timeout: Optional[aiohttp.ClientTimeout] = None):
        # Убедимся, что сессия создана внутри event loop
        await self._ensure_session()
        # Фильтруем None значения из data
        if data and not no_filter_none:
            data = {k: v for k, v in data.items() if v is not None}

        if data:
            data = json.loads(json.dumps(data))  # Преобразуем данные в стандартный формат

        try:
            async with self._semaphore:
                async with self.session.post(f"{self.base_url}{endpoint}", json=data, timeout=timeout or self._timeout) as response:
                    # Пытаемся вернуть JSON, но fallback на текст
                    try:
                        response_data = await response.json()
                    except Exception:
                        response_data = await response.text()
                    status_code = response.status
                    return response_data, status_code
        except asyncio.TimeoutError:
            if getenv("DEBUG", False) == 'true':
                print(f"POST timeout for {endpoint}")
            return {}, 504
        except aiohttp.ClientError as e:
            if getenv("DEBUG", False) == 'true':
                print(f"POST client error for {endpoint}: {e}")
            return {"error": str(e)}, 502

    async def put(self, endpoint: str, data: dict = None, timeout: Optional[aiohttp.ClientTimeout] = None):
        # Убедимся, что сессия создана внутри event loop
        await self._ensure_session()
        # Фильтруем None значения из data
        if data:
            data = {k: v for k, v in data.items() if v is not None}

        if data:
            data = json.loads(json.dumps(data))  # Преобразуем данные в стандартный формат

        try:
            async with self._semaphore:
                async with self.session.put(f"{self.base_url}{endpoint}", json=data, timeout=timeout or self._timeout) as response:
                    try:
                        response_data = await response.json()
                    except Exception:
                        response_data = await response.text()
                    status_code = response.status
                    return response_data, status_code
        except asyncio.TimeoutError:
            if getenv("DEBUG", False) == 'true':
                print(f"PUT timeout for {endpoint}")
            return {}, 504
        except aiohttp.ClientError as e:
            if getenv("DEBUG", False) == 'true':
                print(f"PUT client error for {endpoint}: {e}")
            return {"error": str(e)}, 502

    async def delete(self, endpoint: str, timeout: Optional[aiohttp.ClientTimeout] = None):
        """Выполняет DELETE запрос"""
        # Убедимся, что сессия создана внутри event loop
        await self._ensure_session()
        try:
            async with self._semaphore:
                async with self.session.delete(f"{self.base_url}{endpoint}", timeout=timeout or self._timeout) as response:
                    try:
                        response_data = await response.json()
                    except Exception:
                        # DELETE запросы могут возвращать пустой ответ
                        response_data = {}
                    status_code = response.status
                    return response_data, status_code
        except asyncio.TimeoutError:
            if getenv("DEBUG", False) == 'true':
                print(f"DELETE timeout for {endpoint}")
            return {}, 504
        except aiohttp.ClientError as e:
            if getenv("DEBUG", False) == 'true':
                print(f"DELETE client error for {endpoint}: {e}")
            return {"error": str(e)}, 502

    async def available(self, timeout: Optional[aiohttp.ClientTimeout] = None) -> bool:
        """Проверяет доступность API"""
        # Убедимся, что сессия создана внутри event loop
        await self._ensure_session()
        try:
            async with self._semaphore:
                async with self.session.get(f"{self.base_url}/", timeout=timeout or aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except Exception:
            return False

    async def close(self):
        """Закрывает общую сессию"""
        if self.session is not None and not getattr(self.session, 'closed', False):
            await self.session.close()
            self._closed = True
            if getenv("DEBUG", False) == 'true':
                print("API session closed")

    async def __aenter__(self):
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    def clear_cache(self):
        """Очищает весь кеш"""
        self._cache.clear()
        if getenv("DEBUG", False) == 'true': print("API cache cleared")

    def clear_expired_cache(self):
        """Очищает устаревшие записи из кеша"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time - entry['timestamp'] >= self.CACHE_TIMEOUT
        ]
        for key in expired_keys: del self._cache[key]

        if getenv("DEBUG", False) == 'true':
            print(f"Cleared {len(expired_keys)} expired cache entries")