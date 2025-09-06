import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime

class Logger:
    """
    Статический класс-синглтон для централизованного логирования.
    Каждое приложение может указать своё имя, но все логи пишутся в один файл.
    """
    _instance = None
    _initialized = False
    _handlers = []
    _loggers = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._setup_handlers()
            Logger._initialized = True

    def _setup_handlers(self):
        """Настройка общих обработчиков логирования"""
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_dir = os.getenv("LOG_DIR", "logs")
        self.max_bytes = int(os.getenv("LOG_MAX_BYTES", 50 * 1024 * 1024))  # 50 MB
        self.backup_count = int(os.getenv("LOG_BACKUP_COUNT", 10))
        self.log_format = os.getenv(
            "LOG_FORMAT", 
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        unicorn_logs = os.getenv("UNICORN_LOGS", "false").lower() == "true"

        self.formatter = logging.Formatter(self.log_format)

        # Настройка консольного вывода для Docker
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(self.log_level)
        stream_handler.setFormatter(self.formatter)
        self._handlers.append(stream_handler)

        # Дата без секунд для имен файлов
        self.date_str = datetime.now().strftime("%Y.%m.%d_%H-%M")

        if unicorn_logs:
            for logger_name in ["uvicorn", "uvicorn.error"]:
                # Настройка логгеров uvicorn для лучшей видимости (кроме access логов)
                uvicorn_logger = logging.getLogger(logger_name)
                uvicorn_logger.setLevel(self.log_level)
                uvicorn_logger.propagate = False
                uvicorn_logger.addHandler(stream_handler)

        # Отключаем access логи uvicorn чтобы избежать дублирования с middleware
        uvicorn_access_logger = logging.getLogger("uvicorn.access")
        uvicorn_access_logger.disabled = True

    @classmethod
    def get_logger(cls, name="smm_app"):
        """
        Получить именованный логгер для приложения

        Args:
            name (str): Имя приложения/модуля для логгера

        Returns:
            logging.Logger: Настроенный логгер
        """
        if cls._instance is None:
            cls._instance = cls()

        if name not in cls._instance._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(cls._instance.log_level)
            logger.propagate = False
            
            # Добавляем консольный обработчик (общий для всех)
            for handler in cls._instance._handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
                    logger.addHandler(handler)

            # Создаем отдельный файловый обработчик для каждого логгера
            if cls._instance.log_dir:
                # Создаем папку для логгера
                logger_dir = os.path.join(cls._instance.log_dir, name)
                os.makedirs(logger_dir, exist_ok=True)
                
                # Формируем имя файла: дата_имя_логгера.log
                file_name = os.path.join(logger_dir, f"{cls._instance.date_str}_{name}.log")

                file_handler = RotatingFileHandler(
                    file_name, 
                    maxBytes=cls._instance.max_bytes, 
                    backupCount=cls._instance.backup_count, 
                    encoding="utf-8"
                )
                file_handler.setLevel(cls._instance.log_level)
                file_handler.setFormatter(cls._instance.formatter)
                logger.addHandler(file_handler)

            cls._instance._loggers[name] = logger

        return cls._instance._loggers[name]

    @classmethod
    def debug(cls, message, app_name="smm_app"):
        """Логировать debug сообщение"""
        cls.get_logger(app_name).debug(message)

    @classmethod
    def info(cls, message, app_name="smm_app"):
        """Логировать info сообщение"""
        cls.get_logger(app_name).info(message)

    @classmethod
    def warning(cls, message, app_name="smm_app"):
        """Логировать warning сообщение"""
        cls.get_logger(app_name).warning(message)

    @classmethod
    def error(cls, message, app_name="smm_app"):
        """Логировать error сообщение"""
        cls.get_logger(app_name).error(message)

    @classmethod
    def critical(cls, message, app_name="smm_app"):
        """Логировать critical сообщение"""
        cls.get_logger(app_name).critical(message)