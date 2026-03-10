from urllib.parse import urlparse

def is_valid_telegram_url(url: str) -> bool:
    """
        Проверяет, что URL допустим для кнопок Telegram (нет подчёркиваний в домене).
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ''

        # Telegram не принимает подчёркивания в hostname
        return '_' not in hostname and bool(
            parsed.scheme) and bool(hostname)

    except Exception:
        return False