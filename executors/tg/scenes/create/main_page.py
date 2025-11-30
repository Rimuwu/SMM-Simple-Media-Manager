from datetime import datetime
from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.constants import SETTINGS
from modules.api_client import brain_api, get_users, get_kaiten_users_dict
from tg.oms.common_pages import UserSelectorPage

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

        # Channels
        channels = data.get('channels', [])
        if channels:
            channel_names = []
            for ch_key in channels:
                ch_info = SETTINGS['properties']['channels']['values'].get(ch_key)
                if ch_info:
                    channel_names.append(ch_info['name'])
                else:
                    channel_names.append(ch_key)
            add_vars['channels'] = ', '.join(channel_names)
        else:
            add_vars['channels'] = '⭕'

        tags = data.get('tags')
        if not tags:
            add_vars['tags'] = '⭕'
        else:
            tag_names = []
            for tag_key in tags:
                tag_info = SETTINGS['properties']['tags']['values'].get(tag_key)
                if tag_info:
                    tag_names.append(tag_info['name'])
                else:
                    tag_names.append(tag_key)
            add_vars['tags'] = ', '.join(tag_names)
        
        # Date
        if data.get('publish_date'):
            try:
                dt = datetime.fromisoformat(data['publish_date'])
                add_vars['publish_date'] = dt.strftime('%d.%m.%Y %H:%M')
            except ValueError:
                add_vars['publish_date'] = data['publish_date']
        else:
            add_vars['publish_date'] = '➖'
        
        # Date
        if data.get('send_date'):
            try:
                dt = datetime.fromisoformat(data['send_date'])
                add_vars['send_date'] = dt.strftime('%d.%m.%Y %H:%M')
            except ValueError:
                add_vars['send_date'] = data['send_date']
        else:
            add_vars['send_date'] = '➖'

        # Executor
        user_id = data.get('user')
        if user_id:
            # Получаем информацию о пользователе
            users = await get_users()
            user_data = next((u for u in users if str(u['user_id']) == str(user_id)), None) if users else None

            if user_data:
                kaiten_users = await get_kaiten_users_dict() if user_data.get('tasker_id') else {}
                
                display_name = await UserSelectorPage.get_display_name(
                    user_data, 
                    kaiten_users, 
                    self.scene.__bot__
                )
                add_vars['user'] = display_name
            else:
                add_vars['user'] = f"ID: {user_id}"
        else:
            add_vars['user'] = '➖'

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
    
    
    async def post_buttons(self, 
                           buttons: list[dict]) -> list[dict]:

        buttons_lst = buttons.copy()

        for ind, item in enumerate(buttons_lst):

            if item['callback_data'].split(':')[-1] in [
                'ai-parse', 'finish'
            ]:
                buttons_lst[ind][
                    'ignore_row'] = True
                buttons_lst[ind][
                    'next_line'] = False

        return buttons_lst