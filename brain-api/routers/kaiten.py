from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from modules.kaiten import kaiten
from modules.logs import brain_logger
from models.Card import Card
from uuid import UUID

router = APIRouter(prefix='/kaiten')


@router.get("/get-users")
async def get_users(only_virtual: int = 0):
    async with kaiten as k:
        try:
            users = await k.get_company_users(only_virtual=bool(only_virtual))
        except TypeError:
            users = await k.get_company_users()
            if only_virtual:
                users = [
                    u for u in users
                    if u.get("is_virtual") or u.get("virtual") or u.get("isVirtual")
                ]
        return users


@router.post("/upload-file")
async def upload_file(
    card_id: str = Form(...),  # UUID карточки из базы
    file: UploadFile = File(...)
):
    """
    Загрузить файл в карточку Kaiten.
    
    Args:
        card_id: UUID карточки из базы данных
        file: Файл для загрузки
    
    Returns:
        Информация о загруженном файле
    """
    try:
        # Получаем карточку из базы данных по UUID
        card = await Card.get_by_id(UUID(card_id))
        
        if not card:
            raise HTTPException(status_code=404, detail=f"Карточка с ID {card_id} не найдена")
        
        if not card.task_id:
            raise HTTPException(status_code=400, detail=f"У карточки {card_id} отсутствует task_id для Kaiten")
        
        # Читаем содержимое загруженного файла
        file_data = await file.read()
        
        # Загружаем файл в Kaiten, используя task_id из карточки
        async with kaiten as k:
            file_result = await k.upload_file(
                card_id=card.task_id,  # Используем task_id для Kaiten
                file_data=file_data,  # Передаем бинарные данные
                file_name=file.filename or 'file'
            )
            
            brain_logger.info(
                f"Файл {file.filename} загружен в карточку Kaiten {card.task_id} "
                f"(DB card_id: {card_id})"
            )
            
            return {
                "success": True,
                "file": file_result.to_dict() if hasattr(file_result, 'to_dict') else file_result
            }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Неверный формат UUID: {card_id}")
    except Exception as e:
        brain_logger.error(f"Ошибка загрузки файла в Kaiten: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файла: {str(e)}")
                