from modules.exec import brain_client
from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.constants import CLIENTS


class ForwardToSettingPage(Page):
    """Страница настройки репостов (forward) для Telegram-клиента"""

    __page_name__ = 'client-settings-forward-to'

    async def data_preparate(self):
        card = await self.scene.get_card_data()
        if not card:
            return

        selected_client = self.get_data('selected_client')
        if not selected_client:
            clients = card.get('clients', [])
            if clients:
                selected_client = clients[0]
                await self.scene.update_key('client-settings', 'selected_client', selected_client)

        await self.scene.update_key(self.__page_name__, 'selected_client', selected_client)

    async def content_worker(self) -> str:
        selected_client = self.scene.data.get(self.__page_name__, {}).get('selected_client')
        if not selected_client:
            return "❌ Клиент не выбран"

        card = await self.scene.get_card_data()
        if not card:
            return "❌ Карточка не найдена"

        clients_settings = card.get('clients_settings', {})
        current = clients_settings.get(selected_client, {}).get('forward_to', []) or []

        if not current:
            return f"↪️ Репосты: нет целевых каналов\n\nВыберите каналы, в которые будет репоститься пост из текущего клиента ({selected_client})."

        names = []
        for k in current:
            info = CLIENTS.get(k, {})
            names.append(info.get('label', k))

        return f"↪️ Репосты:\n{', '.join(names)}"

    async def buttons_worker(self) -> list[dict]:
        buttons = []
        selected_client = self.scene.data.get(self.__page_name__, {}).get('selected_client')
        if not selected_client:
            return buttons

        card = await self.scene.get_card_data()
        if not card:
            return buttons

        # Показываем только клиенты с исполнителем telegram и кроме самого источника
        options = [k for k, v in (CLIENTS or {}).items() if (v.get('executor_name') or v.get('executor')) == 'telegram_executor' and k != selected_client]

        clients_settings = card.get('clients_settings', {})
        current = clients_settings.get(selected_client, {}).get('forward_to', []) or []

        for k in options:
            label = CLIENTS.get(k, {}).get('label', k)
            buttons.append({
                'text': (('✅ ' if k in current else '⬜️ ') + label)[:30],
                'callback_data': callback_generator(self.scene.__scene_name__, 'toggle_forward_target', k)
            })

        # only_main_message toggle
        only_main = clients_settings.get(selected_client, {}).get('only_main_message', True)
        buttons.append({
            'text': ('🎯 Только главное сообщение' + (' ✅' if only_main else ' ❌')),
            'callback_data': callback_generator(self.scene.__scene_name__, 'toggle_only_main')
        })

        return buttons

    @Page.on_callback('toggle_forward_target')
    async def toggle_forward_target(self, callback, args):
        if len(args) < 2:
            return await callback.answer('❌ Ошибка')

        tgt = args[1]
        selected_client = self.scene.data.get(self.__page_name__, {}).get('selected_client')
        if not selected_client:
            return await callback.answer('❌ Клиент не выбран')

        # Получаем текущие настройки и переключаем наличие клиента
        card = await self.scene.get_card_data()
        if not card:
            return await callback.answer('❌ Карточка не найдена')

        clients_settings = card.get('clients_settings', {})
        cur = clients_settings.get(selected_client, {})
        forward_list = cur.get('forward_to', []) or []

        if tgt in forward_list:
            forward_list = [c for c in forward_list if c != tgt]
        else:
            forward_list.append(tgt)

        # Сохраняем через brain-api (сохраняем текущее значение only_main_message если есть)
        task_id = self.scene.data['scene'].get('task_id')
        if not task_id:
            return await callback.answer('❌ Задача не найдена')

        # берем текущее значение only_main_message из настроек (если есть)
        only_main = cur.get('only_main_message', True)

        result = await brain_client.set_client_settings(
            card_id=task_id, client_id=selected_client,
            setting_type='forward_to',
            data={'forward_to': forward_list, 'only_main_message': only_main}
        )

        if result and result.get('status', 200) == 200:
            await callback.answer('✅ Настройка сохранена')
            await self.scene.update_message()
        else:
            err = result.get('detail', 'Неизвестная ошибка') if isinstance(result, dict) else 'Ошибка сервера'
            await callback.answer(f'❌ Ошибка: {err}', show_alert=True)

    @Page.on_callback('toggle_only_main')
    async def toggle_only_main(self, callback, args):
        """Toggle only_main_message flag for forward_to"""
        selected_client = self.scene.data.get(self.__page_name__, {}).get('selected_client')
        if not selected_client:
            return await callback.answer('❌ Клиент не выбран')

        card = await self.scene.get_card_data()
        if not card:
            return await callback.answer('❌ Карточка не найдена')

        clients_settings = card.get('clients_settings', {})
        cur = clients_settings.get(selected_client, {})
        only_main = cur.get('only_main_message', True)
        new_val = not bool(only_main)

        # keep existing forward_to list
        forward_list = cur.get('forward_to', []) or []

        task_id = self.scene.data['scene'].get('task_id')
        if not task_id:
            return await callback.answer('❌ Задача не найдена')

        result = await brain_client.set_client_settings(
            card_id=task_id, client_id=selected_client,
            setting_type='forward_to',
            data={'forward_to': forward_list, 'only_main_message': new_val}
        )

        if result and result.get('status', 200) == 200:
            await callback.answer('✅ Настройка сохранена')
            await self.scene.update_message()
        else:
            err = result.get('detail', 'Неизвестная ошибка') if isinstance(result, dict) else 'Ошибка сервера'
            await callback.answer(f'❌ Ошибка: {err}', show_alert=True)

    @Page.on_callback('back')
    async def back(self, callback, args):
        await self.scene.update_page('client-settings-main')