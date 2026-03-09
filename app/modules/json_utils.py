"""
Общий модуль для работы с JSON-конфигурациями и связанными утилитами.
Заменяет json_get.py и json_format.py, убирая дублирование.
"""

import json
from pathlib import Path
from os import getenv
from typing import Any, Dict, Union

BASE_PATH = Path('json/')


# -------------------------------------------------------------
# Чтение JSON файлов
# -------------------------------------------------------------

def open_json_file(filepath: str) -> dict:
    """Загружает JSON-файл из директории ``json/``.

    Возвращает пустой словарь при любой ошибке; ошибки логируются в
    stdout для упрощённой отладки.
    """
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


def open_settings() -> dict:
    """Возвращает словарь из ``json/settings.json``"""
    return open_json_file('settings.json')


def open_clients() -> dict:
    """Возвращает словарь из ``json/clients.json``"""
    return open_json_file('clients.json')


# -------------------------------------------------------------
# Утилиты для обработки значений, возможно содержащих ссылки
# на переменные окружения.
# -------------------------------------------------------------

def value_env(value: Union[str, dict]) -> Union[str, int, bool]:
    """Если ``value`` — словарь с ключом ``'env'``, возвращает значение
    из переменных окружения. Иначе возвращает ``value`` без изменений.

    Пример:
        >>> value_env({'env': 'PORT', 'default': 8080})
    """
    if isinstance(value, dict) and 'env' in value:
        return getenv(value['env'], value.get('default'))
    return value


def check_env_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Рекурсивно обходит словарь и заменяет через :func:`value_env`.
    Используется для конфигураций, где часть полей определяется
    через переменные окружения.
    """
    for key, val in list(config.items()):
        config[key] = value_env(val)
    return config
