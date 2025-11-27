from datetime import datetime
from tg.oms import Page
from tg.oms.utils import callback_generator

class MainPage(Page):
    __page_name__ = 'main'

    async def content_worker(self) -> str:
        self.clear_content()
        add_vars = {}
        data = self.scene.data['scene']

        if data['type'] == 'public':
            add_vars['type'] = 'Общее задание'
        else:
            add_vars['type'] = 'Личное задание'

        if not data['channels']:
            add_vars['channels'] = '⭕'

        if not data['tags']:
            add_vars['tags'] = '⭕'
        
        # Показываем количество файлов
        files = data.get('files', [])
        if files:
            add_vars['files'] = f'📎 {len(files)} файл(ов)'
        else:
            add_vars['files'] = '⭕'

        self.content = self.append_variables(
            **add_vars
        )

        self.content = self.content.replace('None', '➖')

        return self.content

    async def buttons_worker(self) -> list[dict]:
        result = await super().buttons_worker()
        
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
        await self.scene.update_key(
            'scene', 
            'name',
            'Тестовое задание'
        )
        
        await self.scene.update_key(
            'scene', 
            'description',
            'Тестовое описание задания'
        )
        
        await self.scene.update_key(
            'scene', 
            'publish_date',
            datetime.today().isoformat()
        )
        await self.scene.update_message()