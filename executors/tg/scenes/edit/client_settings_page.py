from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.constants import CLIENTS


class ClientSettingsPage(Page):
    """Главная страница настроек клиентов"""
    
    __page_name__ = 'client-settings-main'
    
    # Режим: 'all' (общие настройки) или ключ конкретного клиента
    selected_client = 'all'
    
    async def data_preparate(self):
        """Подготовка данных страницы"""
        card = await self.scene.get_card_data()
        if not card:
            return
        
        # Получаем список клиентов карточки
        clients = card.get('clients', [])
        
        # Если выбранного клиента нет в списке, сбрасываем на 'all'
        if self.selected_client != 'all' and self.selected_client not in clients:
            self.selected_client = 'all'
    
    async def content_worker(self) -> str:
        """Формирование контента страницы"""
        card = await self.scene.get_card_data()
        if not card:
            return "❌ Карточка не найдена"
        
        clients = card.get('clients', [])
        
        if not clients:
            return self.append_variables(
                client_mode="Нет выбранных каналов",
                settings_list="❌ Сначала выберите каналы для публикации"
            )
        
        # Формируем название режима
        if self.selected_client == 'all':
            client_mode = "Общие настройки для всех каналов"
        else:
            client_info = CLIENTS.get(self.selected_client, {})
            client_name = client_info.get('label', self.selected_client)
            client_mode = f"Настройки для: {client_name}"
        
        # Формируем список доступных настроек
        settings_list = self._get_available_settings()
        
        return self.append_variables(
            client_mode=client_mode,
            settings_list=settings_list
        )
    
    def _get_available_settings(self) -> str:
        """Получает список доступных настроек для выбранного клиента"""
        if self.selected_client == 'all':
            return "ℹ️ Выберите конкретный канал для доступа к настройкам"
        
        # Определяем тип исполнителя
        client_info = CLIENTS.get(self.selected_client, {})
        executor_type = client_info.get('executor_name') or client_info.get('executor')

        settings = []

        if executor_type == 'vk_executor':
            settings.append(
                "🖼 Отображение изображений (сетка/карусель)")
        elif executor_type == 'telegram_executor':
            pass  # Entities managed separately
        else:
            settings.append("ℹ️ Нет доступных настроек для этого канала")
        
        return "\n".join(settings) if settings else "ℹ️ Нет доступных настроек"
    
    async def buttons_worker(self) -> list[dict]:
        """Формирование кнопок"""
        buttons = []
        
        card = await self.scene.get_card_data()
        if not card:
            return buttons
        
        clients = card.get('clients', [])
        
        if clients:
            # Кнопка переключения клиента
            if self.selected_client == 'all':
                button_text = '🔄 Режим: Все каналы'
            else:
                client_info = CLIENTS.get(self.selected_client, {})
                client_name = client_info.get('label', self.selected_client)
                button_text = f'🔄 Режим: {client_name}'

            buttons.append({
                'text': button_text,
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 'switch_client'),
                'ignore_row': True
            })
            
            # Кнопки настроек для конкретного клиента
            if self.selected_client != 'all':
                client_info = CLIENTS.get(
                    self.selected_client, {})
                executor_type = client_info.get('executor_name', '') or client_info.get('executor', '')

                if executor_type == 'vk_executor':
                    buttons.append({
                        'text': '🖼 Отображение изображений',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__, 'to_image_view')
                    })

        return buttons

    @Page.on_callback('switch_client')
    async def switch_client(self, callback, args):
        """Переключение между клиентами"""
        card = await self.scene.get_card_data()
        clients = card.get('clients', []) if card else []
        
        if not clients:
            await callback.answer("❌ Сначала выберите каналы для публикации")
            return
        
        # Создаем список доступных режимов: 'all' + клиенты
        available_modes = ['all'] + clients
        
        # Находим текущий индекс
        try:
            current_index = available_modes.index(self.selected_client)
        except ValueError:
            current_index = 0
        
        # Переключаемся на следующий режим (циклично)
        next_index = (current_index + 1) % len(available_modes)
        self.selected_client = available_modes[next_index]
        await self.scene.update_key('client-settings', 
                                    'selected_client', self.selected_client)
        
        # Обновляем сообщение
        await self.scene.update_message()
    
    @Page.on_callback('to_image_view')
    async def to_image_view(self, callback, args):
        """Переход к настройке отображения изображений"""
        if self.selected_client == 'all':
            await callback.answer("❌ Выберите конкретный канал")
            return

        # Сохраняем выбранный клиент в данные сцены
        await self.scene.update_key('client-settings', 'selected_client', self.selected_client)
        await self.scene.update_page('client-settings-image-view')
