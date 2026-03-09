from tg.oms import Page
from tg.oms.utils import callback_generator
from models.Tag import Tag


class TagsListPage(Page):
    __page_name__ = 'tags-list'

    async def data_preparate(self):
        self.tags = [t.to_dict() for t in await Tag.all_sorted()]

    async def content_worker(self) -> str:
        if not self.tags:
            return "🏷 *Управление хештегами*\n\nТегов пока нет. Нажмите «➕ Добавить тег» чтобы создать первый."

        lines = []
        for t in self.tags:
            ftt = f" → topic {t['forward_to_topic']}" if t.get('forward_to_topic') else ""
            lines.append(f"• `{t['key']}` — *{t['name']}* (#{t['tag']}){ftt}")

        return "🏷 *Управление хештегами*\n\n" + "\n".join(lines)

    async def buttons_worker(self):
        buttons = []
        for t in self.tags:
            buttons.append({
                "text": f"✏️ {t['name']}",
                "callback_data": callback_generator(
                    self.scene.__scene_name__,
                    "select-tag",
                    t['key']
                )
            })

        buttons.append({
            "text": "➕ Добавить тег",
            "callback_data": callback_generator(
                self.scene.__scene_name__,
                "add-tag"
            ),
            "ignore_row": True
        })
        return buttons

    @Page.on_callback('select-tag')
    async def on_select_tag(self, callback, args):
        tag_key = args[1]
        await self.scene.update_key('scene', 'selected_tag', tag_key)
        await self.scene.update_page('tag-detail')

    @Page.on_callback('add-tag')
    async def on_add_tag(self, callback, args):
        await self.scene.update_key('scene', 'edit_mode', False)
        await self.scene.update_page('tag-edit-key')
