"""
Модель для работы с файлами карточек Kaiten.
"""

from typing import Optional
from .base import KaitenObject


class File(KaitenObject):
    """
    Класс для работы с файлами карточек Kaiten.
    """
    
    @property
    def name(self) -> Optional[str]:
        """Имя файла."""
        return self._data.get('name')
    
    @property
    def original_name(self) -> Optional[str]:
        """Оригинальное имя файла."""
        return self._data.get('original_name')
    
    @property
    def size(self) -> Optional[int]:
        """Размер файла в байтах."""
        return self._data.get('size')
    
    @property
    def mime_type(self) -> Optional[str]:
        """MIME тип файла."""
        return self._data.get('mime_type')
    
    @property
    def card_id(self) -> Optional[int]:
        """ID карточки, к которой принадлежит файл."""
        return self._data.get('card_id')
    
    @property
    def url(self) -> Optional[str]:
        """URL для скачивания файла."""
        return self._data.get('url')
    
    @property
    def download_url(self) -> Optional[str]:
        """URL для прямого скачивания файла."""
        return self._data.get('download_url')
    
    @property
    def uploaded_at(self) -> Optional[str]:
        """Дата загрузки файла."""
        return self._data.get('uploaded_at')
    
    @property
    def uploader_id(self) -> Optional[int]:
        """ID пользователя, загрузившего файл."""
        return self._data.get('uploader_id')
    
    async def refresh(self) -> 'File':
        """Обновить данные файла из API."""
        # Для файлов нет отдельного эндпоинта получения по ID
        # Нужно получить все файлы карточки и найти нужный
        files_data = await self._client.get_card_files(self.card_id)
        for file_data in files_data:
            if file_data.get('id') == self.id:
                self._data = file_data
                break
        return self
    
    async def delete(self) -> bool:
        """
        Удалить файл.
        
        Returns:
            True если удаление прошло успешно
        """
        return await self._client.delete_file(self.card_id, self.id)
    
    # Файлы не имеют отдельного update метода в API
    def update(self, **fields):
        """Файлы не поддерживают обновление через API."""
        raise NotImplementedError("Files cannot be updated via API")
    
    async def download(self, save_path: Optional[str] = None) -> bytes:
        """
        Скачать файл.
        
        Args:
            save_path: Путь для сохранения файла (опционально)
        
        Returns:
            Содержимое файла в байтах
        """
        if not self.download_url and not self.url:
            raise ValueError("No download URL available for this file")
        
        url = self.download_url or self.url
        
        # Используем сессию клиента для скачивания
        async with self._client.session.get(url) as response:
            if response.status >= 400:
                raise Exception(f"Failed to download file: {response.status}")
            
            content = await response.read()
            
            # Если указан путь для сохранения, сохраняем файл
            if save_path:
                import aiofiles
                async with aiofiles.open(save_path, 'wb') as f:
                    await f.write(content)
            
            return content
    
    def __str__(self) -> str:
        """Строковое представление файла."""
        size_str = f", {self.size} bytes" if self.size else ""
        return f"File(id={self.id}, name='{self.name}'{size_str})"
