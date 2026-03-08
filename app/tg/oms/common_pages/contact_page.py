from urllib.parse import quote
from tg.oms import Page
from modules.exec.brain_client import brain_client
from modules.utils import get_telegram_user, get_user_display_name


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
                cards = await brain_client.get_cards(card_id=card_id)
                task = cards[0] if cards else None
        return task

    async def data_preparate(self) -> None:
        card = await self._get_task_data()
        task_name = card.get('name', 'задаче') if card else 'задаче'
        msg_text = quote(f'Привет. У меня вопрос по задаче "{task_name}"')

        contacts = []
        if card:
            for role_key, label in [
                ('executor_id', 'Исполнитель'),
                ('editor_id', 'Редактор'),
                ('customer_id', 'Заказчик'),
            ]:
                user_db_id = card.get(role_key)
                if not user_db_id:
                    continue
                user = await brain_client.get_user(user_id=user_db_id)
                if not user:
                    continue
                tg_id = user.get('telegram_id')
                if not tg_id:
                    continue
                name = get_user_display_name(user)

                tg_chat = await get_telegram_user(self.scene.__bot__, tg_id)
                if tg_chat and tg_chat.username:
                    url = f"https://t.me/{tg_chat.username}?text={msg_text}"
                else:
                    url = f"tg://user?id={tg_id}"

                contacts.append({'label': label, 'name': name, 'tg_id': tg_id, 'url': url})

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
                'text': f"✉️ {c['label']}: {c['name']}",
                'url': c['url'],
                'ignore_row': True
            })
        return buttons
