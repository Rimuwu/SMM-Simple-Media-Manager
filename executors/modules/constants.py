import json
from typing import Any
from concurrent.futures import ThreadPoolExecutor

# Константы
CLIENTS: dict[str, Any]
EXECUTORS: dict[str, Any]

# Пути к JSON файлам
files = {
    'CLIENTS': 'json/clients.json',
    'EXECUTORS': 'json/executors.json',
}

def load_json(filepath):
    """Загрузка JSON файла"""

    with open(filepath, 'rb') as f:
        return json.loads(f.read())

def load_constants():
    """Параллельная загрузка констант"""

    with ThreadPoolExecutor() as executor:
        results = list(
            executor.map(
                load_json, files.values())
            )
    return dict(zip(files.keys(), results))

constants = load_constants()
globals().update(constants) # Обновляем переменные констант
