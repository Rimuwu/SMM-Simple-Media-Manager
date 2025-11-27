"""
Страница для просмотра и выбора файлов карточки
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram import Bot
from tg.oms import Page
from modules.api_client import get_cards, brain_api


class FilesPage(Page):
    
    __page_name__ = 'files-view'
    
    async def data_preparate(self):
        """Подготовка данных перед отображением"""
        card = await self.scene.get_card_data()
        
        if not card:
            await self.scene.update_key(self.__page_name__, 'files', [])
            return
        
        task_id = card.get('task_id')
        
        try:
            # Запрос файлов карточки
            response, status = await brain_api.get(f"/kaiten/get-files/{task_id}")
            
            if status == 200 and response.get('files'):
                await self.scene.update_key(self.__page_name__, 'files', response['files'])
            else:
                await self.scene.update_key(self.__page_name__, 'files', [])
        except Exception as e:
            print(f"Error getting files: {e}")
            await self.scene.update_key(self.__page_name__, 'files', [])
    
    async def content_worker(self) -> str:
        """Возвращает текст сообщения"""
        return self.append_variables()
    
    async def buttons_worker(self) -> list[dict]:
        """Создает кнопки с файлами"""
        from tg.oms.utils import callback_generator
        
        buttons = []
        files = self.scene.get_key(self.__page_name__, 'files') or []
        
        for file in files:
            file_id = file.get('id')
            file_name = file.get('name', 'Без названия')
            
            # Ограничиваем длину имени для кнопки
            if len(file_name) > 30:
                file_name = file_name[:27] + "..."
            
            buttons.append({
                'text': f"📎 {file_name}",
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'select_file',
                    str(file_id)
                )
            })
        
        return buttons
    
    @Page.on_callback('select_file')
    async def select_file_handler(self, callback: CallbackQuery, args: list):
        """Обработчик выбора файла - показывает превью"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка: не указан ID файла")
            return
        
        file_id = args[1]
        await self.show_file_preview(callback, file_id)
    
    async def show_file_preview(self, callback: CallbackQuery, file_id: str):
        """Показывает превью файла с кнопками"""
        from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
        from tg.oms.utils import callback_generator
        
        card = await self.scene.get_card_data()
        
        if not card:
            await callback.answer("❌ Карточка не найдена")
            return
        
        task_id = card.get('task_id')
        
        try:
            # Получаем бинарные данные файла
            file_data, status = await brain_api.get(
                f"/kaiten/files/{file_id}",
                params={"task_id": task_id},
                return_bytes=True
            )
            
            if status == 200 and isinstance(file_data, bytes):
                # Сохраняем file_id во временные данные страницы
                await self.scene.update_key(self.__page_name__, 'preview_file_id', file_id)
                await self.scene.update_key(self.__page_name__, 'preview_file_data', file_data.hex())
                
                # Создаем кнопки
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Установить",
                            callback_data=callback_generator(
                                self.scene.__scene_name__,
                                'confirm_file',
                                file_id
                            )
                        ),
                        InlineKeyboardButton(
                            text="🗑 Удалить сообщение",
                            callback_data="delete_message"
                        )
                    ]
                ])
                
                # Отправляем фото
                photo = BufferedInputFile(file_data, filename="preview.jpg")
                await callback.message.answer_photo(
                    photo=photo,
                    caption="📷 Предпросмотр изображения\n\nУстановить это изображение для поста?",
                    reply_markup=keyboard
                )
                await callback.answer()
            else:
                await callback.answer("❌ Ошибка при загрузке файла")
        
        except Exception as e:
            print(f"Error showing preview: {e}")
            await callback.answer("❌ Произошла ошибка")
    
    @Page.on_callback('confirm_file')
    async def confirm_file_handler(self, callback: CallbackQuery, args: list):
        """Обработчик подтверждения установки файла"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка: не указан ID файла")
            return
        
        file_id = args[1]
        await self.confirm_file(callback, file_id)
    
    async def confirm_file(self, callback: CallbackQuery, file_id: str):
        """Устанавливает файл в карточку после подтверждения"""
        card = await self.scene.get_card_data()
        
        if not card:
            await callback.answer("❌ Карточка не найдена")
            return
        
        card_id = card.get('card_id')
        
        # Получаем сохраненные данные файла
        file_data_hex = self.scene.get_key(self.__page_name__, 'preview_file_data')
        
        if not file_data_hex:
            await callback.answer("❌ Данные файла не найдены")
            return
        
        try:
            # Отправляем hex данные в API для обновления карточки
            from modules.api_client import update_card
            success = await update_card(
                card_id=card_id,
                binary_data=bytes.fromhex(file_data_hex)
            )
            
            if success:
                await callback.answer("✅ Изображение установлено!")
                # Удаляем сообщение с превью
                try:
                    await callback.message.delete()
                except:
                    pass
                # Обновляем основное сообщение сцены
                await self.scene.update_message()
            else:
                await callback.answer("❌ Ошибка при обновлении карточки")
        
        except Exception as e:
            print(f"Error confirming file: {e}")
            await callback.answer("❌ Произошла ошибка")
