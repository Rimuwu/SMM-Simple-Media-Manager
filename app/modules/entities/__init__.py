from .tg_entities import avaibale_entities as tg_ava
from .vk_entities import avaibale_entities as vk_ava

avaibale_entities = {
    'telegram_executor': tg_ava,
    'vk_executor': vk_ava
}

__all__ = ['avaibale_entities']
