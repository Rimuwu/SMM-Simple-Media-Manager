import os

def value_env(value: str | dict) -> str | int | bool:
    """Работаем со строками / словарями.
    Если значение - словарь и есть ключ 'env', то возвращаем значение из переменных окружения по этому ключу.
    Иначе ничего не делаем.
    Если значения нет в окружении, возвращаем значение ключа 'env' как есть.
    """
    if isinstance(value, dict) and 'env' in value:
        return os.environ.get(value['env'], value['env'])
    return value

def check_env_config(config: dict) -> dict:
    """Проверяем конфиг на наличие переменных окружения"""
    for key, value in config.items():
        config[key] = value_env(value)
    return config