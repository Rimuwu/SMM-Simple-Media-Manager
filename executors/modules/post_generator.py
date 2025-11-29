"""
Модуль для генерации постов с форматированием для различных платформ
"""
from typing import Optional
from modules.constants import CLIENTS, SETTINGS

def generate_post(
    content: str,
    tags: Optional[list[str]] = None,
    platform: str = "telegram",
    client_key: Optional[str] = None
) -> str:
    """
    Генерирует пост с форматированием для указанной платформы.
    
    Args:
        content: Основной текст поста
        tags: Список хештегов
        platform: Платформа для форматирования (telegram, vk, instagram и т.д.)
        client_key: Ключ клиента из clients.json для добавления tag_suffix
    
    Returns:
        Отформатированный текст поста
    """
    post_text = content.strip()
    
    # Добавляем хештеги с суффиксом клиента
    if tags:
        tag_suffix = ""
        if client_key and client_key in CLIENTS:
            tag_suffix = CLIENTS[client_key].get('tag_suffix', '')
        
        hashtags_list = []
        for tag in tags:
            
            tag_name = SETTINGS['properties']['tags']['values'].get(tag, {}).get('tag', tag)
            # Добавляем # если его нет
            formatted_tag = tag_name if tag_name.startswith("#") else f"#{tag_name}"
            # Добавляем суффикс к каждому хештегу
            if tag_suffix:
                formatted_tag = f"{formatted_tag}{tag_suffix}"
            hashtags_list.append(formatted_tag)
        
        # Каждый хештег на отдельной строке
        hashtags = "\n".join(hashtags_list)
        post_text = f"{post_text}\n\n{hashtags}"
    
    # Форматирование в зависимости от платформы
    if platform.lower() == "telegram":
        # Telegram поддерживает HTML и Markdown
        # Здесь можно добавить специфичное форматирование
        pass
    elif platform.lower() == "vk":
        # VK имеет свои особенности форматирования
        pass
    elif platform.lower() == "instagram":
        # Instagram ограничивает длину и не поддерживает ссылки
        pass

    print(post_text)
    
    return post_text


def format_hashtags(tags: list[str]) -> str:
    """
    Форматирует список тегов в строку хештегов.
    
    Args:
        tags: Список тегов
    
    Returns:
        Строка с хештегами
    """
    if not tags:
        return ""
    
    return " ".join([f"#{tag}" if not tag.startswith("#") else tag for tag in tags])


def truncate_post(text: str, max_length: int = 4096) -> str:
    """
    Обрезает текст поста до максимальной длины.
    
    Args:
        text: Текст поста
        max_length: Максимальная длина
    
    Returns:
        Обрезанный текст
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."
