from datetime import datetime
from global_modules.vault.vault_client import vault_getenv as getenv
from modules.utils import get_display_name
from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.constants import SETTINGS
from global_modules.brain_client import brain_client, get_kaiten_users_dict

debug = getenv('DEBUG', 'False') == 'True'

class MainPage(Page):
    __page_name__ = 'main'

    async def content_worker(self) -> str:
        self.clear_content()
        add_vars = {}
        data = self.scene.data['scene']

        # Режим отображения (simple | advanced)
        mode = data.get('mode', 'simple')
        add_vars['mode'] = 'Простой' if mode == 'simple' else 'Продвинутый'

        if data['type'] == 'public':
            add_vars['type'] = 'Общее задание'
        else:
            add_vars['type'] = 'Личное задание'

        # Editor check
        editor_check = data.get('editor_check', True)
        add_vars['editor_check'] = '✅' if editor_check else '❌'

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
            users = await brain_client.get_users()
            user_data = next((u for u in users if str(u['user_id']) == str(user_id)), None) if users else None

            if user_data:
                kaiten_users = await get_kaiten_users_dict() if user_data.get('tasker_id') else {}
                
                display_name = await get_display_name(
                    user_data['telegram_id'],
                    kaiten_users,
                    self.scene.__bot__,
                    user_data.get('tasker_id')
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

            if 'to_page_name' in item and 'style' not in item:
                if item['to_page_name'] in ['finish']:
                    buttons_lst[ind]['style'] = 'success'
                elif item['to_page_name'] in ['cancel']:
                    buttons_lst[ind]['style'] = 'danger'
                elif item['to_page_name'] in [
                    'ai-parse']:
                    buttons_lst[ind]['style'] = 'primary'

        if not self.scene.data['scene']['copywriter_selfcreate']:
            mode = self.scene.data['scene'].get(
                'mode', 'advanced'
                )
            mode_text = f"🧭 Режим: {'Простой' if mode == 'simple' else 'Продвинутый'}"

            buttons_lst.append({
                'text': mode_text,
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 'mode_toggle'
                    ),
                'style': 'primary'
            })

        return buttons_lst

    async def to_page_preworker(self, to_page_buttons: dict) -> dict:
        """Фильтруем кнопки - editor-check только для админов и показываем нужный набор кнопок в зависимости от режима (simple/advanced)
        """
        user_role = await brain_client.get_user_role(self.scene.user_id)

        # Кнопка настройки проверки редактором доступна только админам
        if user_role != 'admin' and 'editor-check' in to_page_buttons:
            del to_page_buttons['editor-check']

        # Режим отображения
        mode = self.scene.data['scene'].get('mode', 'advanced')

        if mode == 'simple':
            allowed = {
                'ai-parse', 'name', 'description', 'send-date', 'publish-date',
                'files', 'help', 'cancel', 'finish'
            }
            to_page_buttons = {k: v for k, v in to_page_buttons.items() if k in allowed}

        return to_page_buttons

    @Page.on_callback('mode_toggle')
    async def mode_toggle_handler(self, callback, args):
        """Обработка нажатия на кнопку режима: переключаем и обновляем сообщение"""
        current = self.scene.data['scene'].get('mode', 'advanced')
        new_mode = 'simple' if current == 'advanced' else 'advanced'
        await self.scene.update_key('scene', 'mode', new_mode)
        await self.scene.update_message()
        return 'exit'
