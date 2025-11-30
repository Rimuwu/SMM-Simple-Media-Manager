import aiohttp
import hashlib
import json
import time
from os import getenv


CACHE_TIMEOUT = 60

class APIClient:

    def __init__(self, base_url: str):
        self.base_url = base_url
        self._cache = {}  # Внутренний кеш для хранения ответов
        self.CACHE_TIMEOUT = CACHE_TIMEOUT

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
                  return_bytes: bool = False):
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

        # Если в кеше нет, делаем запрос
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}{endpoint}", params=params) as response:
                status_code = response.status
                
                if return_bytes:
                    # Возвращаем бинарные данные
                    response_data = await response.read()
                else:
                    # Возвращаем JSON
                    response_data = await response.json()
                    
                    # Кешируем только успешные JSON ответы (статус 200-299)
                    if 200 <= status_code < 300:
                        self._save_to_cache(cache_key, response_data, status_code)
                
                return response_data, status_code

    async def post(self, endpoint: str, data: dict = None):
        # if getenv("DEBUG", False) == 'true': 
        #     print(data)

        # Фильтруем None значения из data
        if data:
            data = {k: v for k, v in data.items() if v is not None}

        if data:
            data = json.loads(json.dumps(data))  # Преобразуем данные в стандартный формат

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}{endpoint}", json=data) as response:
                response_data = await response.json()
                status_code = response.status
                
                return response_data, status_code

    async def put(self, endpoint: str, data: dict = None):
        """Выполняет PUT запрос"""
        if getenv("DEBUG", False) == 'true': 
            print(data)

        # Фильтруем None значения из data
        if data:
            data = {k: v for k, v in data.items() if v is not None}

        if data:
            data = json.loads(json.dumps(data))  # Преобразуем данные в стандартный формат

        async with aiohttp.ClientSession() as session:
            async with session.put(f"{self.base_url}{endpoint}", json=data) as response:
                response_data = await response.json()
                status_code = response.status
                return response_data, status_code

    async def delete(self, endpoint: str):
        """Выполняет DELETE запрос"""
        async with aiohttp.ClientSession() as session:
            async with session.delete(f"{self.base_url}{endpoint}") as response:
                try:
                    response_data = await response.json()
                except:
                    # DELETE запросы могут возвращать пустой ответ
                    response_data = {}
                status_code = response.status
                return response_data, status_code



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