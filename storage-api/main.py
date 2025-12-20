import os
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import logging
from global_modules.logs import Logger
from global_modules.middlewares.logs_mid import RequestLoggingMiddleware

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = Logger().get_logger("storage")

# Создание приложения
app = FastAPI(title="File Storage API", version="1.0.0")
app.add_middleware(RequestLoggingMiddleware, logger=logger)

# Директория для хранения файлов
STORAGE_PATH = Path("/storage")
STORAGE_PATH.mkdir(exist_ok=True, parents=True)

logger.info(f"Storage path: {STORAGE_PATH}")
logger.info(f"Storage path exists: {STORAGE_PATH.exists()}")


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "storage_path": str(STORAGE_PATH),
        "writable": STORAGE_PATH.is_dir() and os.access(STORAGE_PATH, os.W_OK)
    }


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Загрузка файла
    
    Returns:
        dict с filename и оригинальным именем файла
    """
    try:
        # Генерируем уникальное имя файла с расширением оригинального файла
        file_extension = Path(file.filename).suffix if file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = STORAGE_PATH / unique_filename
        
        # Сохраняем файл
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"File uploaded: {unique_filename} (original: {file.filename}, size: {len(content)} bytes)")
        
        return {
            "status": "success",
            "filename": unique_filename,
            "original_filename": file.filename,
            "size": len(content)
        }
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    Скачивание файла по его имени
    """
    try:
        # Защита от path traversal атак
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        file_path = STORAGE_PATH / filename
        
        # Проверяем существование файла
        if not file_path.exists():
            logger.warning(f"File not found: {filename}")
            raise HTTPException(status_code=404, detail="File not found")
        
        logger.info(f"File downloaded: {filename}")
        return FileResponse(file_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@app.delete("/delete/{filename}")
async def delete_file(filename: str):
    """
    Удаление файла
    """
    try:
        # Защита от path traversal атак
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        file_path = STORAGE_PATH / filename
        
        if not file_path.exists():
            logger.warning(f"File not found for deletion: {filename}")
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path.unlink()
        logger.info(f"File deleted: {filename}")
        
        return {"status": "success", "message": f"File {filename} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@app.get("/list")
async def list_files():
    """
    Список всех файлов в хранилище
    """
    try:
        files = []
        for file_path in STORAGE_PATH.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "created": stat.st_mtime
                })
        
        logger.info(f"Listed {len(files)} files")
        return {"status": "success", "count": len(files), "files": files}
    except Exception as e:
        logger.error(f"List error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"List failed: {str(e)}")


@app.get("/info/{filename}")
async def file_info(filename: str):
    """
    Информация о файле
    """
    try:
        # Защита от path traversal атак
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        file_path = STORAGE_PATH / filename
        
        if not file_path.exists():
            logger.warning(f"File not found: {filename}")
            raise HTTPException(status_code=404, detail="File not found")
        
        stat = file_path.stat()
        return {
            "status": "success",
            "filename": filename,
            "size": stat.st_size,
            "created": stat.st_mtime,
            "path": str(file_path)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Info error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Info failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="warning")
