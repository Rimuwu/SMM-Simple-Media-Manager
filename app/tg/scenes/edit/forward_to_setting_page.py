from models.Card import Card
from uuid import UUID as _UUID
from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.constants import CLIENTS


def _get_forward_list(clients_settings: dict, selected_client: str) -> list:
    """Нормализует legacy-вложенные структуры, возвращая плоский список forward_to."""
    cur = clients_settings.get(selected_client, {})
    val = cur.get('forward_to', [])
    if isinstance(val, dict):
        val = val.get('forward_to', [])
        if isinstance(val, dict):
            val = val.get('forward_to', [])
    return val if isinstance(val, list) else []


def _get_only_main(clients_settings: dict, selected_client: str) -> bool:
    """Нормализует legacy-вложенные структуры, возвращая флаг only_main_message."""
    cur = clients_settings.get(selected_client, {})
    if 'only_main_message' in cur:
        return bool(cur['only_main_message'])
    fwd = cur.get('forward_to', {})
    if isinstance(fwd, dict):
        return bool(fwd.get('only_main_message', True))
    return True


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
        current = _get_forward_list(clients_settings, selected_client)

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
        current = _get_forward_list(clients_settings, selected_client)

        for k in options:
            label = CLIENTS.get(k, {}).get('label', k)
            buttons.append({
                'text': (('✅ ' if k in current else '⬜️ ') + label)[:30],
                'callback_data': callback_generator(self.scene.__scene_name__, 'toggle_forward_target', k)
            })

        # only_main_message toggle
        only_main = _get_only_main(clients_settings, selected_client)
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
        forward_list = _get_forward_list(clients_settings, selected_client)

        if tgt in forward_list:
            forward_list = [c for c in forward_list if c != tgt]
        else:
            forward_list = forward_list + [tgt]

        task_id = self.scene.data['scene'].get('task_id')
        if not task_id:
            return await callback.answer('❌ Задача не найдена')

        card_obj = await Card.get_by_id(_UUID(str(task_id)))
        if not card_obj:
            return await callback.answer('❌ Задача не найдена')

        await card_obj.set_client_setting_type(selected_client, 'forward_to', forward_list)
        await callback.answer('✅ Настройка сохранена')
        await self.scene.update_message()

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
        only_main = _get_only_main(clients_settings, selected_client)
        new_val = not only_main

        task_id = self.scene.data['scene'].get('task_id')
        if not task_id:
            return await callback.answer('❌ Задача не найдена')

        card_obj2 = await Card.get_by_id(_UUID(str(task_id)))
        if not card_obj2:
            return await callback.answer('❌ Задача не найдена')

        await card_obj2.set_client_setting_type(selected_client, 'only_main_message', new_val)
        await callback.answer('✅ Настройка сохранена')
        await self.scene.update_message()

    @Page.on_callback('back')
    async def back(self, callback, args):
        await self.scene.update_page('client-settings-main')