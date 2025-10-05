from tg.oms import Page

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

        self.content = self.append_variables(
            **add_vars
        )

        self.content = self.content.replace('None', '➖')

        return self.content