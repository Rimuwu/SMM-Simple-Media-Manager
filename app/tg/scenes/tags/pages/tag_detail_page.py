from tg.oms import Page
from tg.oms.utils import callback_generator
from app.models.card.Tag import Tag


class TagDetailPage(Page):
    __page_name__ = 'tag-detail'

    async def data_preparate(self):
        tag_key = self.scene.data['scene'].get('selected_tag')
        self.tag = None
        if tag_key:
            t = await Tag.get_by_key("key", tag_key)
            self.tag = t.to_dict() if t else None

    async def content_worker(self) -> str:
        if not self.tag:
            return "❌ Тег не найден."

        ftt = str(self.tag['forward_to_topic']) if self.tag.get('forward_to_topic') else 'Нет'
        return (
            f"🏷 *Тег: {self.tag['name']}*\n\n"
            f"🔑 Ключ: `{self.tag['key']}`\n"
            f"#️⃣ Хештег: #{self.tag['tag']}\n"
            f"📌 Порядок: {self.tag['order']}\n"
            f"📨 Forward to topic: {ftt}"
        )

    async def buttons_worker(self):
        return [
            {
                "text": "✏️ Изменить название",
                "callback_data": callback_generator(self.scene.__scene_name__, "edit-tag-name")
            },
            {
                "text": "#️⃣ Изменить хештег",
                "callback_data": callback_generator(self.scene.__scene_name__, "edit-tag-tag")
            },
            {
                "text": "📨 Изменить forward topic",
                "callback_data": callback_generator(self.scene.__scene_name__, "edit-tag-ftt")
            },
            {
                "text": "🔢 Изменить порядок",
                "callback_data": callback_generator(self.scene.__scene_name__, "edit-tag-order")
            },
            {
                "text": "🗑 Удалить тег",
                "callback_data": callback_generator(self.scene.__scene_name__, "delete-tag"),
                "ignore_row": True
            },
            {
                "text": "🔙 Назад",
                "callback_data": callback_generator(self.scene.__scene_name__, "tags-list"),
                "ignore_row": True
            },
        ]

    @Page.on_callback('edit-tag-name')
    async def on_edit_name(self, callback, args):
        await self.scene.update_key('scene', 'edit_field', 'name')
        await self.scene.update_page('tag-edit-text')

    @Page.on_callback('edit-tag-tag')
    async def on_edit_tag(self, callback, args):
        await self.scene.update_key('scene', 'edit_field', 'tag')
        await self.scene.update_page('tag-edit-text')

    @Page.on_callback('edit-tag-ftt')
    async def on_edit_ftt(self, callback, args):
        await self.scene.update_key('scene', 'edit_field', 'forward_to_topic')
        await self.scene.update_page('tag-edit-int')

    @Page.on_callback('edit-tag-order')
    async def on_edit_order(self, callback, args):
        await self.scene.update_key('scene', 'edit_field', 'order')
        await self.scene.update_page('tag-edit-int')

    @Page.on_callback('delete-tag')
    async def on_delete(self, callback, args):
        tag_key = self.scene.data['scene'].get('selected_tag')
        if tag_key:
            t = await Tag.get_by_key("key", tag_key)
            if t:
                await t.delete()
            await callback.answer("✅ Тег удалён")
            await self.scene.update_page('tags-list')
        else:
            await callback.answer("❌ Тег не найден", show_alert=True)

    @Page.on_callback('tags-list')
    async def on_back(self, callback, args):
        await self.scene.update_page('tags-list')
