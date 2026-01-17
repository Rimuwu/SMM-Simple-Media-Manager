"""
Роутер для работы с файлами карточек
Файлы хранятся в storage_api, информация о них - в БД
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from uuid import UUID as _UUID
import logging
import aiohttp
from models.Card import Card
from models.CardFile import CardFile
from modules.api_client import storage_api
from modules.logs import brain_logger as logger

router = APIRouter(prefix='/files')


def _to_iso(v):
    return v.isoformat() if v else None

async def _find_card_by_id(card_id: str):
    """Надёжно находит карточку по id (строка, UUID или как str(UUID))."""
    # Пробуем точный поиск
    card = await Card.get_by_key('card_id', card_id)
    if card:
        logger.debug(f"Found card by direct match: {card_id}")
        return card

    # Пробуем как UUID
    try:
        parsed = _UUID(card_id)
        card = await Card.get_by_key('card_id', parsed)
        if card:
            logger.debug(f"Found card by UUID parse: {card_id}")
            return card
    except Exception:
        parsed = None

    # Фоллбэк: ограниченный скан недавних карточек (лучше чем полный scan)
    try:
        candidates = await Card.get_all(limit=200)
        for c in candidates:
            if str(c.card_id) == card_id:
                logger.debug(f"Found card by str() match: {card_id}")
                return c
    except Exception:
        logger.exception("Error scanning cards in _find_card_by_id")

    return None


class FileUploadResponse(BaseModel):
    id: str
    card_id: str
    filename: str
    original_filename: str
    size: int
    order: int


class FileInfoResponse(BaseModel):
    id: str
    card_id: str
    filename: str
    original_filename: str
    size: int
    data_info: dict
    order: int
    hide: bool = False
    created_at: Optional[str] = None


@router.post("/upload/{card_id}")
async def upload_file_to_card(card_id: str, file: UploadFile = File(...)):
    """
    Загрузить файл к карточке.
    Сначала загружается в storage_api, затем создаётся запись в БД.
    
    Args:
        card_id: ID карточки
        file: Файл для загрузки
    
    Returns:
        Информация о загруженном файле
    """
    try:
        # Проверяем существование карточки (устойчивый поиск)
        card = await _find_card_by_id(card_id)
        if not card:
            logger.warning(f"Upload attempt for non-existing card_id: {card_id}")
            raise HTTPException(status_code=404, detail="Card not found")
        
        # Загружаем файл в storage_api
        logger.info(f"Uploading file {file.filename} to card {card_id}")
        
        content = await file.read()
        
        # Отправляем файл в storage_api напрямую (multipart/form-data)
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file', content, filename=file.filename, content_type=file.content_type)
                async with session.post(f"{storage_api.base_url}/upload", data=data, timeout=300) as resp:
                    storage_status = resp.status
                    try:
                        storage_response = await resp.json()
                    except Exception:
                        storage_response = {"status": "error", "error": "invalid response"}
        except Exception as e:
            logger.error(f"Failed to upload file to storage_api: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
        
        if storage_status != 200 or storage_response.get('status') != 'success':
            logger.error(f"Storage API upload failed: status={storage_status}, resp={storage_response}")
            raise HTTPException(status_code=500, detail="Storage API upload failed")
        
        # Создаём запись в БД
        filename = storage_response.get('filename')
        original_filename = storage_response.get('original_filename')
        size = storage_response.get('size', 0)
        
        # Получаем максимальный порядок
        existing_files = await CardFile.filter_by(card_id=card_id)
        max_order = max([f.order for f in existing_files], default=-1) if existing_files else -1
        
        card_file = await CardFile.create(
            card_id=card_id,
            filename=filename,
            original_filename=original_filename,
            size=size,
            data_info={"mime_type": file.content_type},
            order=max_order + 1
        )
        
        logger.info(f"File {filename} uploaded to card {card_id}")
        
        return FileUploadResponse(
            id=str(card_file.id),
            card_id=str(card_file.card_id),
            filename=card_file.filename,
            original_filename=card_file.original_filename,
            size=card_file.size,
            order=card_file.order
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@router.get("/download/{file_id}")
async def download_file(file_id: str):
    """
    Скачать файл по его ID
    
    Args:
        file_id: ID файла в БД
    
    Returns:
        Бинарные данные файла
    """
    try:
        # Получаем информацию о файле из БД
        card_file = await CardFile.get_by_key('id', file_id)
        if not card_file:
            raise HTTPException(status_code=404, detail="File not found")
        
        logger.info(f"Downloading file {card_file.filename}")
        
        # Скачиваем из storage_api (возвращаем бинарные данные)
        try:
            data, status = await storage_api.get(f'/download/{card_file.filename}', return_bytes=True)
            if status != 200:
                logger.error(f"Failed to download file from storage_api: status={status}")
                raise HTTPException(status_code=500, detail="Failed to download file")

            from fastapi.responses import Response
            mime = (card_file.data_info or {}).get('mime_type') if card_file.data_info else None
            return Response(content=data, media_type=mime or 'application/octet-stream')
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to download file from storage_api: {e}")
            raise HTTPException(status_code=500, detail="Failed to download file")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")


@router.get("/list/{card_id}")
async def list_card_files(card_id: str):
    """
    Список всех файлов карточки
    
    Args:
        card_id: ID карточки
    
    Returns:
        Список файлов с информацией
    """
    try:
        # Проверяем существование карточки (устойчивый поиск)
        card = await _find_card_by_id(card_id)
        if not card:
            logger.warning(f"List files attempt for non-existing card_id: {card_id}")
            raise HTTPException(status_code=404, detail="Card not found")
        
        # Получаем файлы в порядке сортировки
        files = await CardFile.filter_by(card_id=card_id)
        files.sort(key=lambda f: getattr(f, 'order', 0))
        
        logger.info(f"Listed {len(files)} files for card {card_id}")
        
        return {
            "count": len(files),
            "files": [
                FileInfoResponse(
                    id=str(f.id),
                    card_id=str(f.card_id),
                    filename=f.filename,
                    original_filename=f.original_filename,
                    size=f.size,
                    data_info=f.data_info,
                    order=f.order,
                    hide=f.hide,
                    created_at=_to_iso(getattr(f, 'created_at', None))
                ).dict()
                for f in files
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")


@router.get("/info/{file_id}")
async def get_file_info(file_id: str):
    """
    Получить информацию о файле
    
    Args:
        file_id: ID файла
    
    Returns:
        Информация о файле
    """
    try:
        card_file = await CardFile.get_by_key('id', file_id)
        if not card_file:
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileInfoResponse(
            id=str(card_file.id),
            card_id=str(card_file.card_id),
            filename=card_file.filename,
            original_filename=card_file.original_filename,
            size=card_file.size,
            data_info=card_file.data_info,
            order=card_file.order,
            hide=card_file.hide,
            created_at=_to_iso(getattr(card_file, 'created_at', None))
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting file info: {str(e)}")


@router.delete("/delete/{file_id}")
async def delete_file(file_id: str):
    """
    Удалить файл (удаляется и из storage_api, и из БД)
    
    Args:
        file_id: ID файла
    
    Returns:
        Статус удаления
    """
    try:
        card_file = await CardFile.get_by_key('id', file_id)
        if not card_file:
            raise HTTPException(status_code=404, detail="File not found")
        
        filename = card_file.filename
        logger.info(f"Deleting file {filename}")
        
        # Удаляем из storage_api
        try:
            await storage_api.delete(f'/delete/{filename}')
        except Exception as e:
            logger.warning(f"Failed to delete file from storage_api: {e}")
            # Продолжаем, удаляем запись из БД в любом случае
        
        # Удаляем запись из БД
        await card_file.delete()
        
        logger.info(f"File {filename} deleted successfully")
        
        return {"status": "success", "message": f"File {filename} deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")


class ReorderFilesRequest(BaseModel):
    file_ids: list[str]  # Список file_id в нужном порядке


@router.post("/toggle-hide/{file_id}")
async def toggle_file_hide(file_id: str):
    """
    Переключить скрытие файла
    
    Args:
        file_id: ID файла
    
    Returns:
        Обновленная информация о файле
    """
    try:
        card_file = await CardFile.get_by_key('id', file_id)
        if not card_file:
            raise HTTPException(status_code=404, detail="File not found")
        
        new_hide_value = not card_file.hide
        await card_file.update(hide=new_hide_value)
        
        logger.info(f"File {card_file.filename} hide toggled to {new_hide_value}")
        
        return FileInfoResponse(
            id=str(card_file.id),
            card_id=str(card_file.card_id),
            filename=card_file.filename,
            original_filename=card_file.original_filename,
            size=card_file.size,
            data_info=card_file.data_info,
            order=card_file.order,
            hide=new_hide_value,
            created_at=_to_iso(getattr(card_file, 'created_at', None))
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling file hide: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error toggling file hide: {str(e)}")


@router.post("/reorder/{card_id}")
async def reorder_files(card_id: str, request: ReorderFilesRequest):
    """
    Изменить порядок файлов в карточке
    
    Args:
        card_id: ID карточки
        request: Список file_id в нужном порядке
    
    Returns:
        Статус изменения
    """
    try:
        # Проверяем существование карточки
        card = await _find_card_by_id(card_id)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        # Обновляем порядок для каждого файла
        for order, file_id in enumerate(request.file_ids):
            card_file = await CardFile.get_by_key('id', file_id)
            if not card_file or str(card_file.card_id) != card_id:
                raise HTTPException(status_code=400, detail=f"File {file_id} not found in card")
            
            await card_file.update(order=order)
        
        logger.info(f"Files reordered for card {card_id}")
        
        return {"status": "success", "message": "Files reordered successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reordering files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error reordering files: {str(e)}")
