"""
Модуль для работы с JSON конфигурационными файлами.
"""
import json
from pathlib import Path

BASE_PATH = Path('json/')


def open_json_file(filepath: str) -> dict:
    """Загружает JSON файл"""
    try:
        with open(BASE_PATH / filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {filepath}")
        return {}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {}


def open_properties() -> dict:
    """Возвращает свойства из settings.json"""
    return open_json_file('settings.json').get('properties', {})


def open_settings() -> dict:
    """Возвращает настройки из settings.json"""
    return open_json_file('settings.json')


def open_clients() -> dict:
    """Возвращает клиентов из clients.json"""
    return open_json_file('clients.json')
