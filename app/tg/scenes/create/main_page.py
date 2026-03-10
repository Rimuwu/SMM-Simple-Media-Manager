import copy
from datetime import datetime
from os import getenv
from tg.oms import Page
from tg.oms.utils import callback_generator

debug = getenv('DEBUG', 'False') == 'True'

class MainPage(Page):
    __page_name__ = 'main'

    async def content_worker(self) -> str:
        self.clear_content()
        add_vars = {}
        data = self.scene.data['scene']

        # Инфо текущего задания
        task = self.scene.data.get('task', {})
        queued_cards = self.scene.data.get('cards', [])
        add_vars['task_name'] = task.get('name') or 'Не задано'
        add_vars['posts_count'] = str(len(queued_cards))

        if data['type'] == 'public':
            add_vars['type'] = 'Общее задание'
        else:
            add_vars['type'] = 'Личное задание'

        # Дата отправки
        if data.get('send_date'):
            try:
                dt = datetime.fromisoformat(data['send_date'])
                add_vars['send_date'] = dt.strftime('%d.%m.%Y %H:%M')
            except ValueError:
                add_vars['send_date'] = data['send_date']
        else:
            add_vars['send_date'] = '➖'

        # Показываем количество файлов
        files = data.get('files', [])
        if files:
            add_vars['files'] = f'📎 {len(files)} файл(ов)'
        else:
            add_vars['files'] = '0 прикреплено'
            
        if data.get('description'):
            add_vars['description'] = data['description']
        else:
            add_vars['description'] = 'Без описания'

        self.content = self.append_variables(**add_vars)
        self.content = self.content.replace('None', '➖')

        return self.content

    async def buttons_worker(self) -> list[dict]:
        result = await super().buttons_worker()

        if debug:
            result.append(
                {
                    'text': 'Тестовые данные',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'test_data'
                    )
                }
            )

        return result

    @Page.on_callback('test_data')
    async def test_data_handler(self, callback, args):
        await self.scene.update_key('scene', 'name', 'Тестовое задание')
        await self.scene.update_key('scene', 'description', 'Тестовое описание задания')
        await self.scene.update_message()

    async def post_buttons(self, buttons: list[dict]) -> list[dict]:

        buttons_lst = buttons.copy()

        for ind, item in enumerate(buttons_lst):
            if item['callback_data'].split(':')[-1] in ['ai-parse', 'finish']:
                buttons_lst[ind]['ignore_row'] = True
                buttons_lst[ind]['next_line'] = False

            if 'to_page_name' in item and 'style' not in item:
                if item['to_page_name'] in ['finish']:
                    buttons_lst[ind]['style'] = 'success'
                elif item['to_page_name'] in ['cancel']:
                    buttons_lst[ind]['style'] = 'danger'
                elif item['to_page_name'] in ['ai-parse']:
                    buttons_lst[ind]['style'] = 'primary'

        # Кнопка "Добавить пост в задание" видна, если заполнено название поста
        if self.scene.data['scene'].get('name'):
            buttons_lst.append({
                'text': '💾 Добавить пост в задание',
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 'save_to_task'
                ),
                'ignore_row': True,
            })

        return buttons_lst

    @Page.on_callback('save_to_task')
    async def save_to_task(self, callback, args):
        """Сохранить текущий пост в список задания и вернуться на главную страницу задания."""
        data = self.scene.data['scene']
        if not data.get('name'):
            await callback.answer('Укажите хотя бы название поста', show_alert=True)
            return

        card_data = copy.deepcopy(data)
        cards = list(self.scene.data.get('cards', []))
        cards.append(card_data)
        self.scene.data['cards'] = cards

        # Сбрасываем данные текущей карточки до значений по умолчанию
        default = copy.deepcopy(self.scene.scene.standart_data)
        self.scene.data['scene'].update(default)
        await self.scene.save_to_db()

        await callback.answer(f'✅ Пост «{card_data["name"]}» добавлен в задание')
        await self.scene.update_page('task-main')
        return 'exit'
