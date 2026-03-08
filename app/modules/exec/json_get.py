import json
from typing import Any

BASE_PATH = "/json"


def open_json_file(filepath: str) -> dict | None:
    """
    Загружает JSON файл по указанному пути.
    
    Args:
        filepath: Путь к JSON файлу
        
    Returns:
        dict или None при ошибке
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON decode error in {filepath}: {e}")
        return None


def open_settings(base_path: str = BASE_PATH) -> dict | None:
    """
    Загружает файл settings.json.
    
    Args:
        base_path: Базовый путь к папке json
        
    Returns:
        dict с настройками или None
    """
    return open_json_file(f'{base_path}/settings.json')


def open_clients(base_path: str = BASE_PATH) -> dict | None:
    """
    Загружает файл clients.json.
    
    Args:
        base_path: Базовый путь к папке json
        
    Returns:
        dict с клиентами или None
    """
    return open_json_file(f'{base_path}/clients.json')


def open_properties(base_path: str = BASE_PATH) -> dict | None:
    """
    Загружает файл properties.json.
    
    Args:
        base_path: Базовый путь к папке json
        
    Returns:
        dict со свойствами или None
    """
    return open_json_file(
        f'{base_path}/settings.json').get(
        'properties', {}
        ) if open_json_file(
            f'{base_path}/settings.json') else {}


def open_executors(base_path: str = BASE_PATH) -> dict | None:
    """
    Загружает файл executors.json.
    
    Args:
        base_path: Базовый путь к папке json
        
    Returns:
        dict с исполнителями или None
    """
    return open_json_file(f'{base_path}/executors.json')


def save_json_file(filepath: str, data: Any) -> bool:
    """
    Сохраняет данные в JSON файл.
    
    Args:
        filepath: Путь к JSON файлу
        data: Данные для сохранения
        
    Returns:
        True при успехе, False при ошибке
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving JSON to {filepath}: {e}")
        return False
