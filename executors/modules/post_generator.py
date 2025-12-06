"""
Модуль для генерации постов с форматированием для различных платформ
"""
import re
from typing import Optional
from modules.constants import CLIENTS, SETTINGS


def clean_html(text: str) -> str:
    """
    Удаляет HTML теги из текста.
    
    Args:
        text: Текст с HTML тегами
    
    Returns:
        Очищенный текст без HTML тегов
    """
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def convert_hyperlinks_to_vk(text: str) -> str:
    """
    Конвертирует HTML гиперссылки в VK формат.
    Ссылки на vk.com конвертируются в [ссылка|текст].
    Остальные ссылки просто извлекают текст.
    
    Args:
        text: Текст с HTML гиперссылками
    
    Returns:
        Текст с конвертированными ссылками
    """
    # Паттерн для поиска <a href="...">текст</a>
    pattern = r'<a\s+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>'
    
    def replace_link(match):
        url = match.group(1)
        link_text = match.group(2)
        
        # Если ссылка на vk.com, конвертируем в VK формат
        if 'vk.com' in url:
            return f'[{url}|{link_text}]'
        else:
            # Для остальных ссылок просто оставляем текст и URL
            return f'{link_text} ({url})'
    
    return re.sub(pattern, replace_link, text, flags=re.IGNORECASE)


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
        # Оставляем как есть
        pass
    elif platform.lower() == "vk":
        # VK имеет свои особенности форматирования
        # Конвертируем гиперссылки vk.com в VK формат
        post_text = convert_hyperlinks_to_vk(post_text)
        # Очищаем оставшиеся HTML теги
        post_text = clean_html(post_text)

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
