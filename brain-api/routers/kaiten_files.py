"""
Роутер для работы с файлами Kaiten
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from modules.kaiten import kaiten
from modules.logs import brain_logger
from fastapi_cache.decorator import cache

router = APIRouter(prefix='/kaiten')


@router.get("/get-files/{task_id}")
async def get_card_files(task_id: int):
    """
    Получает список файлов карточки Kaiten.
    
    Args:
        task_id: ID карточки в Kaiten
    
    Returns:
        Список файлов
    """
    try:
        async with kaiten as k:
            files = await k.get_card_files(task_id)
            
            files_list = []
            for file in files:
                files_list.append({
                    "id": file.id,
                    "name": file.name,
                    "size": file.size,
                    "url": file.url
                })
            
            return {
                "success": True,
                "files": files_list
            }
    
    except Exception as e:
        brain_logger.error(f"Ошибка получения файлов из Kaiten: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка получения файлов: {str(e)}")


@router.get("/files/{file_id}")
async def download_file(file_id: int, task_id: int):
    """
    Скачивает файл из Kaiten.
    
    Args:
        file_id: ID файла
        task_id: ID карточки в Kaiten (в query параметрах)
    
    Returns:
        Бинарные данные файла
    """
    try:
        async with kaiten as k:
            # Получаем информацию о файле
            files = await k.get_card_files(task_id)
            target_file = None
            
            for file in files:
                if file.id == file_id:
                    target_file = file
                    break
            
            if not target_file:
                raise HTTPException(status_code=404, detail="Файл не найден")
            
            if not target_file.url:
                raise HTTPException(status_code=400, detail="URL файла не найден")
            
            # Скачиваем файл по URL
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(target_file.url) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=response.status,
                            detail="Ошибка при скачивании файла"
                        )
                    
                    file_data = await response.read()
            
            # Возвращаем файл как бинарные данные
            return Response(
                content=file_data,
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": f'attachment; filename="{target_file.name}"'
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        brain_logger.error(f"Ошибка скачивания файла из Kaiten: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка скачивания файла: {str(e)}")
