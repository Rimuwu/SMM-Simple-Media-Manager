from urllib.parse import quote
from tg.oms import Page
from models.Card import Card
from models.User import User
from uuid import UUID as _UUID
from modules.utils import get_telegram_user, get_user_display_name
from tg.scenes.constants import ROLE_ICONS


class ContactPage(Page):
    """Страница 'Связь' — кнопки для перехода в ЛС к участникам задачи с заготовленным текстом."""

    __page_name__ = 'contact'

    async def _get_task_data(self) -> dict | None:
        """Универсальный метод получения данных задачи для обеих сцен."""
        if hasattr(self.scene, 'get_card_data'):
            return await self.scene.get_card_data()

        task = self.scene.data['scene'].get('current_task_data')
        if not task:
            card_id = self.scene.data['scene'].get('selected_task')
            if card_id:
                cards = [c.to_dict() for c in await Card.find(card_id=card_id)]
                task = cards[0] if cards else None
        return task

    async def data_preparate(self) -> None:
        card = await self._get_task_data()
        task_name = card.get('name', 'задаче') if card else 'задаче'

        bot_username = (await self.scene.bot.get_me()).username
        view_link = f't.me/{bot_username}?start=type-open-view_id-{card["card_id"]}'

        contacts = []
        if card:
            for role_key, label, role_text, emoji_key in [
                ('executor_id', 'Исполнитель', 'исполнителем', 'copywriter'),
                ('editor_id', 'Редактор', 'редактором', 'editor'),
                ('customer_id', 'Заказчик', 'заказчиком', 'customer'),
            ]:
                user_db_id = card.get(role_key)
                if not user_db_id:
                    continue

                user_obj = await User.get_by_id(_UUID(str(user_db_id)))
                user = user_obj.to_dict() if user_obj else None
                if not user:
                    continue

                tg_id = user.get('telegram_id')
                if not tg_id:
                    continue

                name = get_user_display_name(user)
                msg_text = quote(f'Привет! У меня вопрос по задаче «{task_name}» по которой ты назначен(а) {role_text}.\nПосмотреть задачу: {view_link}\n\n...')

                tg_chat = await get_telegram_user(self.scene.__bot__, tg_id)
                if tg_chat and tg_chat.username:
                    url = f"t.me/{tg_chat.username}?text={msg_text}"
                else:
                    url = f"tg://user?id={tg_id}"

                contacts.append({'label': f'{ROLE_ICONS.get(emoji_key)} {label}', 
                                 'name': name, 
                                 'tg_id': tg_id, 
                                 'url': url})

        await self.scene.update_key(self.__page_name__, 'contacts', contacts)

    async def content_worker(self) -> str:
        contacts = self.scene.get_key(self.__page_name__, 'contacts') or []
        if not contacts:
            return '📭 *Связь*\n\nУчастники задачи не назначены.'

        lines = ['📬 *Связь с участниками задачи*\n']
        for c in contacts:
            lines.append(f"• {c['label']}: *{c['name']}*")
        lines.append('\nНажмите на кнопку ниже, чтобы написать участнику в личные сообщения.')
        return '\n'.join(lines)

    async def buttons_worker(self) -> list[dict]:
        contacts = self.scene.get_key(self.__page_name__, 'contacts') or []
        buttons = []
        for c in contacts:
            buttons.append({
                'text': f"{c['label']}: {c['name']}",
                'url': c['url'],
                'ignore_row': True
            })
        return buttons
