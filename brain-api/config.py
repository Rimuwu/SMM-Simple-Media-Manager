from pydantic_settings import BaseSettings
from os import getenv


class Settings(BaseSettings):

    # База данных
    database_url: str = getenv("DATABASE_URL")

    # Настройки логирования
    log_level: str = "INFO"
    log_dir: str = "logs"
    log_max_bytes: int = 50 * 1024 * 1024
    log_backup_count: int = 10
    log_format: str = "%(asctime)s %(levelname)s %(message)s"
    unicorn_logs: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Создаем экземпляр настроек
settings = Settings()
