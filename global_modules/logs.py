import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime

settings = {}

# Настройка логгера
log_level = getattr(settings, "log_level", "INFO")
log_dir = getattr(settings, "log_dir", "logs")
max_bytes = getattr(settings, "log_max_bytes", 50 * 1024 * 1024)  # 50 MB
backup_count = getattr(settings, "log_backup_count", 10)
log_format = getattr(settings, "log_format", "%(asctime)s %(levelname)s %(message)s")
unicorn_logs = getattr(settings, "unicorn_logs", False)

logger = logging.getLogger("smm_app")
logger.setLevel(log_level)
logger.propagate = False

formatter = logging.Formatter(log_format)

# Настройка консольного вывода для Docker
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(log_level)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
file_name = f'{log_dir}/{now_str}.log'

# Настройка файлового логирования
if log_dir:
    os.makedirs(
        os.path.dirname(file_name), 
        exist_ok=True)

    file_handler = RotatingFileHandler(
        file_name, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

if unicorn_logs:
    for logger_name in ["uvicorn", "uvicorn.error"]:
        # Настройка логгеров uvicorn для лучшей видимости (кроме access логов)
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.setLevel(log_level)
        uvicorn_logger.propagate = False
        uvicorn_logger.addHandler(stream_handler)

# Отключаем access логи uvicorn чтобы избежать дублирования с middleware
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.disabled = True