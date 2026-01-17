from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.api_client import brain_api

types = {
    'poll': 'Опрос',
    'inline_keyboard': 'Клавиатура ссылок',
}

class EntityViewPage(Page):
    __page_name__ = 'entities-view'

    async def data_preparate(self):
        eid = self.scene.data.get('entities-main', {}).get('view_entity_id')
        task_id = self.scene.data['scene'].get('task_id')
        if not task_id or not eid:
            return
        selected_client = self.scene.data.get('entities-main', {}).get('selected_client')
        if not selected_client:
            return

        resp, status = await brain_api.get(f'/card/entity?card_id={task_id}&client_id={selected_client}&entity_id={eid}')
        if status == 200 and resp:
            await self.scene.update_key(self.__page_name__, 'entity', resp)

    async def content_worker(self) -> str:
        e = self.scene.data.get(self.__page_name__, {}).get('entity')
        if not e:
            return '❌ Entity не найден'

        txt = [
            f"Тип: {types.get(e.get('type'), e.get('type'))}", 
            f"Имя: {e.get('data', {}).get('name') or e.get('type')}", 
            f"ID: {e.get('id')}\n"
        ]
        data = e.get('data') or {}

        if e.get('type') == 'poll':
            txt.append(f"Вопрос: {data.get('question')}")
            opts = data.get('options', [])
            for i, o in enumerate(opts, 1):
                txt.append(f"{i}. {o}")

        elif e.get('type') == 'inline_keyboard':
            buttons = data.get('buttons', [])
            if buttons:
                txt.append(f"Кнопок: {len(buttons)}")
                for i, btn in enumerate(buttons, 1):
                    txt.append(f"{i}. {btn.get('text')} → {btn.get('url')}")
            else:
                txt.append("Нет кнопок")

        return "\n".join(txt)

    async def buttons_worker(self):
        buttons = []
        buttons.append({
            'text': '🗑 Удалить',
            'callback_data': callback_generator(self.scene.__scene_name__, 'delete'),
            'ignore_row': True
        })

        buttons.append({
            'text': '✏️ Редактировать',
            'callback_data': callback_generator(self.scene.__scene_name__, 'edit'),
            'ignore_row': True
        })

        return buttons

    @Page.on_callback('delete')
    async def delete(self, callback, args):
        e = self.scene.data.get(self.__page_name__, {}).get('entity')
        if not e:
            await callback.answer('❌ Entity не найден')
            return

        task_id = self.scene.data['scene'].get('task_id')
        if not task_id:
            await callback.answer('❌ Задача не найдена')
            return

        selected_client = self.scene.data.get('entities-main', {}).get('selected_client')
        resp, status = await brain_api.post('/card/delete-entity', data={
            'card_id': task_id,
            'client_id': selected_client,
            'entity_id': e.get('id')
        })

        if status == 200:
            await callback.answer('✅ Entity удалён')
            await self.scene.update_page('entities-main')
            await self.scene.update_message()
        else:
            await callback.answer('❌ Ошибка удаления')

    @Page.on_callback('edit')
    async def edit(self, callback, args):
        e = self.scene.data.get(self.__page_name__, {}).get('entity')
        if not e:
            await callback.answer('❌ Entity не найден')
            return

        selected_client = self.scene.data.get('entities-main', {}).get('selected_client')
        if not selected_client:
            await callback.answer('❌ Клиент не выбран')
            return

        entity_type = e.get('type')
        entity_data = e.get('data', {})
        entity_id = e.get('id')

        # Определяем страницу в зависимости от типа entity
        if entity_type == 'poll':
            page_name = 'entities-poll-create'
        elif entity_type == 'inline_keyboard':
            page_name = 'entities-keyboard-create'
        else:
            await callback.answer(f'❌ Неизвестный тип entity: {entity_type}')
            return

        # Подготовить данные для страницы редактирования и перейти на неё
        await self.scene.update_key(page_name, 'data', entity_data)
        await self.scene.update_key(page_name, 'entity_id', entity_id)
        await self.scene.update_page(page_name)
        await self.scene.update_message()

    @Page.on_callback('back')
    async def back(self, callback, args):
        await self.scene.update_page('entities-main')
        await self.scene.update_message()
