from app.models.card.Card import Card
from uuid import UUID as _UUID
from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.constants import CLIENTS


class ImageViewSettingPage(Page):
    """Страница настройки отображения изображений для VK"""
    
    __page_name__ = 'client-settings-image-view'
    
    async def data_preparate(self):
        """Подготовка данных страницы"""
        # Получаем выбранный клиент из данных сцены
        selected_client = self.get_data('selected_client')

        if not selected_client:
            print("No selected client found, trying to set a default one.")
            # Если клиент не выбран, берем первого из списка
            card = await self.scene.get_card_data()
            if card:
                clients = card.get('clients', [])
                if clients:
                    selected_client = clients[0]
                    await self.scene.update_key('client-settings', 'selected_client', selected_client)
        
        # Сохраняем в данные страницы
        await self.scene.update_key(self.__page_name__, 'selected_client', selected_client)
    
    async def content_worker(self) -> str:
        """Формирование контента страницы"""
        selected_client = self.scene.data.get(self.__page_name__, {}).get('selected_client')
        
        if not selected_client:
            return "❌ Клиент не выбран"
        
        # Получаем информацию о клиенте
        client_info = CLIENTS.get(selected_client, {})
        client_name = client_info.get('label', selected_client)
        
        # Получаем текущую настройку из карточки
        card = await self.scene.get_card_data()
        if not card:
            return "❌ Карточка не найдена"
        
        clients_settings = card.get('clients_settings', {})
        raw_view = clients_settings.get(selected_client, {}).get('image_view', 'grid')
        current_setting = raw_view.get('type', 'grid') if isinstance(raw_view, dict) else (raw_view or 'grid')
        
        # Формируем описание
        if current_setting == 'grid':
            current_text = "🔲 Сетка (Grid)"
            description = "Изображения отображаются в виде сетки. Подходит для нескольких фотографий."
        else:
            current_text = "🎠 Карусель (Carousel)"
            description = "Изображения отображаются в виде карусели. Пользователь может листать их."
        
        return self.append_variables(
            client_name=client_name,
            current_setting=current_text,
            setting_description=description
        )
    
    async def buttons_worker(self) -> list[dict]:
        """Формирование кнопок"""
        buttons = []
        
        selected_client = self.scene.data.get(self.__page_name__, {}).get('selected_client')
        
        if not selected_client:
            return buttons
        
        # Получаем текущую настройку
        card = await self.scene.get_card_data()
        if not card:
            return buttons

        clients_settings = card.get('clients_settings', {})
        raw_view = clients_settings.get(selected_client, {}).get('image_view', 'grid')
        current_setting = raw_view.get('type', 'grid') if isinstance(raw_view, dict) else (raw_view or 'grid')
        
        # Кнопки выбора типа отображения
        buttons.append({
            'text': '🔲 Сетка (Grid)' + (' ✅' if current_setting == 'grid' else ''),
            'callback_data': callback_generator(
                self.scene.__scene_name__, 'set_view', 'grid')
        })
        
        buttons.append({
            'text': '🎠 Карусель (Carousel)' + (' ✅' if current_setting == 'carousel' else ''),
            'callback_data': callback_generator(
                self.scene.__scene_name__, 'set_view', 'carousel')
        })
        
        return buttons
    
    @Page.on_callback('set_view')
    async def set_view(self, callback, args):
        """Установка типа отображения изображений"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка: не указан тип отображения")
            return
        
        view_type = args[1]  # 'grid' или 'carousel'
        
        if view_type not in ['grid', 'carousel']:
            await callback.answer("❌ Неверный тип отображения")
            return
        
        selected_client = self.scene.data.get(self.__page_name__, {}).get('selected_client')
        
        if not selected_client:
            await callback.answer("❌ Клиент не выбран")
            return
        
        # Получаем task_id
        task_id = self.scene.data['scene'].get('task_id')
        if not task_id:
            await callback.answer("❌ Задача не найдена")
            return
        
        # Отправляем запрос на обновление настройки
        card_obj = await Card.get_by_id(_UUID(str(task_id)))
        if not card_obj:
            await callback.answer("❌ Задача не найдена")
            return

        await card_obj.set_client_setting_type(selected_client, 'image_view', view_type)
        view_name = "сетка" if view_type == 'grid' else "карусель"
        await callback.answer(f"✅ Настройка изменена: {view_name}")
        await self.scene.update_message()
