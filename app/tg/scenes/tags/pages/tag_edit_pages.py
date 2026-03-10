from tg.oms import Page
from tg.oms.utils import callback_generator
from app.models.card.Tag import Tag


# Поля, которые редактируются как текст
_FIELD_LABELS = {
    'name': 'название',
    'tag': 'хештег (без #)',
    'forward_to_topic': 'ID топика для пересылки (число или 0 чтобы убрать)',
    'order': 'порядок сортировки (число)',
}

# Используется и для текстовых полей (name, tag)
class TagEditTextPage(Page):
    __page_name__ = 'tag-edit-text'

    async def data_preparate(self):
        self.edit_field = self.scene.data['scene'].get('edit_field', 'name')

    async def content_worker(self) -> str:
        label = _FIELD_LABELS.get(self.edit_field, self.edit_field)
        return f"✏️ *Редактирование тега*\n\nВведите новое *{label}*:"

    async def buttons_worker(self):
        return [{
            "text": "🔙 Назад",
            "callback_data": callback_generator(self.scene.__scene_name__, "tag-detail"),
            "ignore_row": True
        }]

    @Page.on_text('str')
    async def on_text(self, message, value: str):
        value = value.strip().lstrip('#')
        tag_key = self.scene.data['scene'].get('selected_tag')
        field = self.scene.data['scene'].get('edit_field', 'name')
        t = await Tag.get_by_key("key", tag_key)
        if t:
            await t.update(**{field: value})
        await self.scene.update_page('tag-detail')

    @Page.on_callback('tag-detail')
    async def on_back(self, callback, args):
        await self.scene.update_page('tag-detail')


# Для числовых полей (forward_to_topic, order)
class TagEditIntPage(Page):
    __page_name__ = 'tag-edit-int'

    async def data_preparate(self):
        self.edit_field = self.scene.data['scene'].get('edit_field', 'order')

    async def content_worker(self) -> str:
        label = _FIELD_LABELS.get(self.edit_field, self.edit_field)
        return f"✏️ *Редактирование тега*\n\nВведите новое значение — *{label}*:"

    async def buttons_worker(self):
        buttons = []
        if self.edit_field == 'forward_to_topic':
            buttons.append({
                "text": "🗑 Убрать (нет топика)",
                "callback_data": callback_generator(self.scene.__scene_name__, "clear-ftt"),
            })
        buttons.append({
            "text": "🔙 Назад",
            "callback_data": callback_generator(self.scene.__scene_name__, "tag-detail"),
            "ignore_row": True
        })
        return buttons

    @Page.on_text('int')
    async def on_int(self, message, value: int):
        tag_key = self.scene.data['scene'].get('selected_tag')
        field = self.scene.data['scene'].get('edit_field', 'order')
        update_val = value if value != 0 or field == 'order' else None
        t = await Tag.get_by_key("key", tag_key)
        if t:
            await t.update(**{field: update_val})
        await self.scene.update_page('tag-detail')

    @Page.on_callback('clear-ftt')
    async def on_clear_ftt(self, callback, args):
        tag_key = self.scene.data['scene'].get('selected_tag')
        t = await Tag.get_by_key("key", tag_key)
        if t:
            await t.update(forward_to_topic=None)
        await callback.answer("✅ Топик убран")
        await self.scene.update_page('tag-detail')

    @Page.on_callback('tag-detail')
    async def on_back(self, callback, args):
        await self.scene.update_page('tag-detail')
