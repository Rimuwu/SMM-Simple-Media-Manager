from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.exec.brain_client import brain_client


class TagCreateKeyPage(Page):
    """Шаг 1: ввод уникального ключа нового тега."""
    __page_name__ = 'tag-edit-key'

    async def content_worker(self) -> str:
        return (
            "➕ *Добавление нового тега*\n\n"
            "Шаг 1 из 3\n\n"
            "Введите уникальный *ключ* тега (латиница, без пробелов).\n"
            "Пример: `dota2`, `cs2`, `content`"
        )

    async def buttons_worker(self):
        return [{
            "text": "🔙 Назад",
            "callback_data": callback_generator(self.scene.__scene_name__, "tags-list"),
            "ignore_row": True
        }]

    @Page.on_text('str')
    async def on_text(self, message, value: str):
        key = value.strip().lower().replace(' ', '_')
        await self.scene.update_key('scene', 'new_tag_key', key)
        await self.scene.update_page('tag-create-name')

    @Page.on_callback('tags-list')
    async def on_back(self, callback, args):
        await self.scene.update_page('tags-list')


class TagCreateNamePage(Page):
    """Шаг 2: ввод отображаемого имени нового тега."""
    __page_name__ = 'tag-create-name'

    async def content_worker(self) -> str:
        key = self.scene.data['scene'].get('new_tag_key', '')
        return (
            f"➕ *Добавление нового тега*\n\n"
            f"Ключ: `{key}`\n\n"
            f"Шаг 2 из 3\n\n"
            f"Введите *название* тега (отображается в интерфейсе).\n"
            f"Пример: `Dota 2`, `Counter-Strike 2`"
        )

    async def buttons_worker(self):
        return [{
            "text": "🔙 Назад",
            "callback_data": callback_generator(self.scene.__scene_name__, "tag-edit-key"),
            "ignore_row": True
        }]

    @Page.on_text('str')
    async def on_text(self, message, value: str):
        await self.scene.update_key('scene', 'new_tag_name', value.strip())
        await self.scene.update_page('tag-create-hashtag')

    @Page.on_callback('tag-edit-key')
    async def on_back(self, callback, args):
        await self.scene.update_page('tag-edit-key')


class TagCreateHashtagPage(Page):
    """Шаг 3: ввод хештега (без #) и сохранение."""
    __page_name__ = 'tag-create-hashtag'

    async def content_worker(self) -> str:
        key = self.scene.data['scene'].get('new_tag_key', '')
        name = self.scene.data['scene'].get('new_tag_name', '')
        return (
            f"➕ *Добавление нового тега*\n\n"
            f"Ключ: `{key}`\n"
            f"Название: *{name}*\n\n"
            f"Шаг 3 из 3\n\n"
            f"Введите *хештег* (без решётки #).\n"
            f"Пример: `Dota2`, `CS2`, `Content`"
        )

    async def buttons_worker(self):
        return [{
            "text": "🔙 Назад",
            "callback_data": callback_generator(self.scene.__scene_name__, "tag-create-name"),
            "ignore_row": True
        }]

    @Page.on_text('str')
    async def on_text(self, message, value: str):
        key = self.scene.data['scene'].get('new_tag_key', '')
        name = self.scene.data['scene'].get('new_tag_name', '')
        tag = value.strip().lstrip('#')

        # Считаем порядок: в конец списка
        existing = await brain_client.get_tags()
        order = len(existing)

        result = await brain_client.create_tag(key=key, name=name, tag=tag, order=order)
        if result:
            await self.scene.update_key('scene', 'selected_tag', key)
            await self.scene.update_page('tag-detail')
        else:
            await self.scene.update_page('tags-list')

    @Page.on_callback('tag-create-name')
    async def on_back(self, callback, args):
        await self.scene.update_page('tag-create-name')
