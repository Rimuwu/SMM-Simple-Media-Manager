"""
Модуль хранения файлов.

В монолите заменяет HTTP-вызовы к storage-api прямыми файловыми операциями.
Путь к хранилищу настраивается через переменную окружения STORAGE_PATH.
"""
import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional

from os import getenv
from modules.logs import logger


STORAGE_PATH = Path('/storage_data')
STORAGE_PATH.mkdir(parents=True, exist_ok=True)


async def upload_file(
    file_data: bytes,
    filename: str,
    content_type: Optional[str] = None
) -> dict:
    """
    Сохранить файл в хранилище.
    Заменяет: storage_api.post("/upload", multipart)

    Returns:
        {"status": "success", "filename": unique_name, "original_filename": filename, "size": int}
        или {"status": "error", "error": str}
    """
    try:
        file_extension = Path(filename).suffix if filename else ""
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = STORAGE_PATH / unique_filename

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write_file, file_path, file_data)

        logger.info(f"File saved: {unique_filename} (original: {filename}, size: {len(file_data)} bytes)")
        return {
            "status": "success",
            "filename": unique_filename,
            "original_filename": filename,
            "size": len(file_data),
        }
    except Exception as e:
        logger.error(f"Ошибка сохранения файла {filename}: {e}")
        return {"status": "error", "error": str(e)}


def _write_file(path: Path, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)


async def download_file(filename: str) -> tuple[bytes | None, int]:
    """
    Скачать файл из хранилища по имени.
    Заменяет: /download/{filename} или /files/download/{file_id} (через brain->storage)

    Returns:
        (bytes, 200) или (None, 404/500)
    """
    try:
        file_path = STORAGE_PATH / filename
        if not file_path.exists():
            logger.warning(f"File not found: {filename}")
            return None, 404

        # Security: ensure we stay within STORAGE_PATH
        file_path = file_path.resolve()
        if not str(file_path).startswith(str(STORAGE_PATH.resolve())):
            logger.error(f"Path traversal attempt: {filename}")
            return None, 403

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, file_path.read_bytes)
        return data, 200
    except Exception as e:
        logger.error(f"Ошибка чтения файла {filename}: {e}")
        return None, 500


async def delete_file(filename: str) -> bool:
    """
    Удалить файл из хранилища.
    Заменяет: storage_api.delete(f'/delete/{filename}')
    """
    try:
        file_path = (STORAGE_PATH / filename).resolve()
        if not str(file_path).startswith(str(STORAGE_PATH.resolve())):
            logger.error(f"Path traversal attempt on delete: {filename}")
            return False

        if file_path.exists():
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, file_path.unlink)
            logger.info(f"File deleted: {filename}")
            return True
        return True  # Идемпотентное удаление
    except Exception as e:
        logger.error(f"Ошибка удаления файла {filename}: {e}")
        return False


def file_exists(filename: str) -> bool:
    """Проверить наличие файла в хранилище."""
    return (STORAGE_PATH / filename).exists()


def get_storage_path() -> Path:
    """Получить путь к директории хранилища."""
    return STORAGE_PATH
