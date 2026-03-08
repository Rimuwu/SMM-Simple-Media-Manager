from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.constants import CLIENTS
from modules.exec import brain_client


class AutoPinSettingPage(Page):
    """Страница настройки автозакрепа (Telegram)"""

    __page_name__ = 'client-settings-auto-pin'

    async def data_preparate(self):
        card = await self.scene.get_card_data()
        if not card:
            return

        selected_client = self.get_data('selected_client')
        if not selected_client:
            # Попробуем взять первый клиент как fallback
            clients = card.get('clients', [])
            if clients:
                selected_client = clients[0]
                await self.scene.update_key('client-settings', 'selected_client', selected_client)

        await self.scene.update_key(self.__page_name__, 'selected_client', selected_client)
        await self.scene.update_key(self.__page_name__, 'currentsetting', '✅ Включён' if card.get('clients_settings', {}).get(selected_client, {}).get('auto_pin', False) else '❌ Выключен')

    async def content_worker(self) -> str:
        selected_client = self.scene.data.get(self.__page_name__, {}).get('selected_client')
        if not selected_client:
            return "❌ Клиент не выбран"

        card = await self.scene.get_card_data()
        if not card:
            return "❌ Карточка не найдена"

        clients_settings = card.get('clients_settings', {})
        current = clients_settings.get(selected_client, {}).get('auto_pin', False)

        status_text = '✅ Включён' if current else '❌ Выключен'
        return self.append_variables(
            client_name=CLIENTS.get(selected_client, {}).get('label', selected_client),
            current_status=status_text
        )

    async def buttons_worker(self) -> list[dict]:
        buttons = []
        selected_client = self.scene.data.get(self.__page_name__, {}).get('selected_client')
        if not selected_client:
            return buttons

        card = await self.scene.get_card_data()
        if not card:
            return buttons

        clients_settings = card.get('clients_settings', {})
        current = clients_settings.get(selected_client, {}).get('auto_pin', False)

        buttons.append({
            'text': '🔛 Включить',
            'callback_data': callback_generator(self.scene.__scene_name__, 'set_auto_pin', 'true'),
            'style': 'success' if current else None
        })
        buttons.append({
            'text': '⛔ Отключить',
            'callback_data': callback_generator(self.scene.__scene_name__, 'set_auto_pin', 'false'),
            'style': 'danger' if not current else None
        })

        return buttons

    @Page.on_callback('set_auto_pin')
    async def set_auto_pin(self, callback, args):
        if len(args) < 2:
            return await callback.answer('❌ Ошибка')

        val = args[1].lower()
        if val not in ('true', 'false'):
            return await callback.answer('❌ Некорректное значение')

        enabled = True if val == 'true' else False

        selected_client = self.scene.data.get(self.__page_name__, {}).get('selected_client')
        if not selected_client:
            return await callback.answer('❌ Клиент не выбран')

        task_id = self.scene.data['scene'].get('task_id')
        if not task_id:
            return await callback.answer('❌ Задача не найдена')

        result = await brain_client.set_client_settings(
            card_id=task_id,
            client_id=selected_client,
            setting_type='auto_pin',
            data={'enabled': enabled}
        )

        if result and result.get('status', 200) == 200:
            await callback.answer('✅ Автозакреп обновлён')
            await self.scene.update_message()
        else:
            err = result.get('detail', 'Неизвестная ошибка') if isinstance(result, dict) else 'Ошибка сервера'
            await callback.answer(f'❌ Ошибка: {err}', show_alert=True)

    @Page.on_callback('back')
    async def back(self, callback, args):
        await self.scene.update_page('client-settings-main')