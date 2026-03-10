from datetime import datetime
from tg.oms.utils import callback_generator
from tg.oms import Page
from models.User import User
from models.CardFile import CardFile
from modules.card import card_service
from uuid import UUID as _UUID
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class FinishPage(Page):

    __page_name__ = 'finish'

    # Флаг, указывающий что создание в процессе — используется для скрытия кнопки
    creating: bool = False

    def _task_flow(self) -> bool:
        """True если пользователь создаёт задание с несколькими постами."""
        return bool(self.scene.data.get('cards'))

    def min_values(self) -> bool:
        if self._task_flow():
            task = self.scene.data.get('task', {})
            return bool(task.get('name') and self.scene.data.get('cards'))
        # Прямое создание одной карточки — достаточно названия
        data = self.scene.data['scene']
        return bool(data.get('name'))

    async def buttons_worker(self) -> list[dict]:
        buttons = []
        if self.min_values() and not getattr(self, 'creating', False):
            buttons.append({
                'text': '❤ Создать',
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 'end'),
                'ignore_row': True,
                'style': 'success',
            })
        return buttons

    async def content_worker(self) -> str:
        if getattr(self, 'creating', False):
            return '🧸 Создание задания...'

        if self._task_flow():
            return await self._task_flow_content()
        return await self._single_card_content()

    # ── Контент для мульти-пост задания ──────────────────────────────────────

    async def _task_flow_content(self) -> str:
        task = self.scene.data.get('task', {})
        cards = self.scene.data.get('cards', [])

        task_name = task.get('name') or '➖'
        task_desc = task.get('description') or 'Без описания'
        task_deadline = task.get('deadline')
        if task_deadline:
            try:
                dt = datetime.fromisoformat(task_deadline)
                task_deadline = dt.strftime('%d.%m.%Y %H:%M')
            except Exception:
                pass
        else:
            task_deadline = '➖'

        posts_list = ''
        for i, card in enumerate(cards, 1):
            posts_list += f'\n  {i}. `{card.get("name", "...")}`'

        content = (
            f"✅ *Подтверждение создания задания*\n\n"
            f"📋 *Задание:*\n"
            f"📌 Название: `{task_name}`\n"
            f"📄 Описание: `{task_desc}`\n"
            f"📅 Дедлайн: {task_deadline}\n\n"
            f"📮 *Посты ({len(cards)}):*{posts_list}"
        )

        if not self.min_values():
            content += '\n\n❗️ Укажите название задания и добавьте хотя бы один пост.'

        return content

    # ── Контент для одиночной карточки (обратная совместимость) ──────────────

    async def _single_card_content(self) -> str:
        data = self.scene.data['scene']

        type_label = 'Общее задание' if data.get('type') == 'public' else 'Личное задание'

        if data.get('send_date'):
            try:
                dt = datetime.fromisoformat(data['send_date'])
                send_date_str = dt.strftime('%d.%m.%Y %H:%M')
            except ValueError:
                send_date_str = data['send_date']
        else:
            send_date_str = '➖'

        files = data.get('files', [])
        files_str = f'📎 {len(files)} файл(ов)' if files else '⭕'
        description = data.get('description') or 'Без описания'

        content = (
            f"✅ *Подтверждение создания поста*\n\n"
            f"📌 Название: `{data.get('name', '➖')}`\n"
            f"📄 Описание: `{description}`\n"
            f"📋 Тип: {type_label}\n"
            f"📅 Дата публикации: {send_date_str}\n"
            f"📁 Файлы: {files_str}"
        )

        if not self.min_values():
            content += '\n\n❗️ Не все обязательные поля заполнены.'

        return content

    # ── Создание ─────────────────────────────────────────────────────────────

    @Page.on_callback('end')
    async def on_end(self, callback, args):
        await callback.answer('Создание...')
        self.creating = True
        await self.scene.update_message()

        customers = await User.find(telegram_id=self.scene.user_id)
        customer_id = customers[0].user_id if customers else None

        try:
            if self._task_flow():
                await self._create_task_with_cards(customer_id)
            else:
                await self._create_single_card(customer_id)
        except Exception as e:
            print(f"Ошибка создания: {e}")
            self.creating = False
            self.clear_content()
            await self.scene.update_message()
            await self.scene.__bot__.send_message(
                self.scene.user_id,
                f'❌ Произошла ошибка при создании: {str(e)[:1024]}'
            )

    async def _create_task_with_cards(self, customer_id):
        """Создать Task + все посты из scene.data['cards']."""
        task_data = self.scene.data.get('task', {})
        cards_data = self.scene.data.get('cards', [])

        task = await card_service.create_task(
            title=task_data['name'],
            description=task_data.get('description'),
            deadline=task_data.get('deadline'),
            customer_id=customer_id,
            executor_id=task_data.get('executor'),
        )
        if not task:
            self.creating = False
            await self.scene.update_message()
            await self.scene.__bot__.send_message(
                self.scene.user_id, '❌ Ошибка при создании задания.')
            return

        task_id = task.task_id
        created_cards = []

        for card_data in cards_data:
            res = await card_service.create_card(
                title=card_data.get('name', ''),
                description=card_data.get('description', ''),
                send_time=card_data.get('send_date'),
                image_prompt=card_data.get('image'),
                type_id=card_data.get('type', 'public'),
                task_id=task_id,
            )
            if res:
                created_cards.append(res)
                files = card_data.get('files', [])
                if files:
                    await CardFile.upload_many(
                        card_id=str(res.card_id),
                        files=files,
                        bot=self.scene.__bot__,
                    )

        await self.scene.end()

        bot_username = (await self.scene.__bot__.get_me()).username
        msg = (
            f'✅ Задание *«{task_data["name"]}»* создано\n'
            f'📮 Постов создано: {len(created_cards)} из {len(cards_data)}\n'
            f'🆔 ID задания: `{str(task.task_id)[:8]}...`'
        )
        markup = None
        if created_cards:
            first_id = str(created_cards[0].card_id)
            view_link = f'https://t.me/{bot_username}?start=type-open-view_id-{first_id}'
            markup = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text='Просмотреть первый пост', url=view_link)
            ]])

        await self.scene.__bot__.send_message(
            self.scene.user_id, msg, parse_mode='Markdown', reply_markup=markup)

    async def _create_single_card(self, customer_id):
        """Создать одну карточку (обратная совместимость с прямым потоком)."""
        data = self.scene.data['scene']

        task_data = self.scene.data.get('task', {})
        task = await card_service.create_task(
            title=task_data.get('name') or data['name'],
            description=task_data.get('description') or data.get('description'),
            deadline=task_data.get('deadline'),
            customer_id=customer_id,
            executor_id=task_data.get('executor'),
        )
        task_id = task.task_id if task else None

        res = await card_service.create_card(
            title=data['name'],
            description=data.get('description', ''),
            send_time=data.get('send_date'),
            image_prompt=data.get('image'),
            type_id=data.get('type', 'public'),
            task_id=task_id,
        )

        if not res:
            self.creating = False
            self.clear_content()
            await self.scene.update_message()
            await self.scene.__bot__.send_message(
                self.scene.user_id, '❌ Произошла ошибка при создании задачи.')
            return

        card_id = str(res.card_id)
        files = data.get('files', [])
        uploaded_count = 0
        if files:
            uploaded_count = await CardFile.upload_many(
                card_id=card_id, files=files, bot=self.scene.__bot__)

        await self.scene.end()

        bot_username = (await self.scene.__bot__.get_me()).username
        view_link = f'https://t.me/{bot_username}?start=type-open-view_id-{card_id}'
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='Просмотреть задачу', url=view_link)
        ]])
        await self.scene.__bot__.send_message(
            self.scene.user_id,
            f'Задача: "{data["name"]}" успешно создана\nID: {card_id}\n'
            f'📎 Загружено файлов: {uploaded_count}',
            reply_markup=markup,
        )
