from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.constants import CLIENTS
from models.Entity import Entity
from uuid import UUID as _UUID


class EntitiesMainPage(Page):
    __page_name__ = 'entities-main'
    
    selected_client = None

    async def data_preparate(self):
        """Load entities data"""
        task_id = self.scene.data['scene'].get('task_id')
        if not task_id:
            return
        
        card = await self.scene.get_card_data()
        if card:
            clients = card.get('clients', [])
            if not self.selected_client and clients:
                self.selected_client = clients[0]

    async def content_worker(self) -> str:
        card = await self.scene.get_card_data()
        if not card:
            return '❌ Карточка не найдена'
        
        clients = card.get('clients', [])
        if not clients:
            return 'ℹ️ _Сначала выберите каналы для публикации_'

        if not self.selected_client:
            self.selected_client = clients[0]

        client_info = CLIENTS.get(self.selected_client, {})
        client_name = client_info.get('label', self.selected_client)

        task_id = self.scene.data['scene'].get('task_id')
        if not task_id:
            return '❌ Задача не найдена'
        
        entities = [e.to_dict() for e in await Entity.filter_by(card_id=_UUID(str(task_id)), client_key=self.selected_client)]

        types = {
            'poll': 'Опрос',
            'inline_keyboard': 'Клавиатура ссылок',
        }

        if entities is None:
            entities_list = '_Ошибка загрузки_'
        elif not entities:
            entities_list = '_Нет entities для этого канала_'
        else:
            lines = []
            for e in entities:
                title = e.get('data', {}).get('name') or e.get('type')
                lines.append(f"• {types.get(e.get('type'), e.get('type'))} - {title}")
            entities_list = "\n".join(lines)
        
        return self.append_variables(
            client_name=client_name,
            entities_list=entities_list
        )

    async def buttons_worker(self) -> list[dict]:
        buttons = []
        
        card = await self.scene.get_card_data()
        if not card:
            return buttons
        
        clients = card.get('clients', [])
        if not clients:
            return buttons
        
        # Switch client button
        if not self.selected_client:
            self.selected_client = clients[0]
        
        client_info = CLIENTS.get(self.selected_client, {})
        client_name = client_info.get('label', self.selected_client)
        
        buttons.append({
            'text': f'🔄 Канал: {client_name}',
            'callback_data': callback_generator(self.scene.__scene_name__, 'switch_client'),
            'ignore_row': True
        })

        executor = client_info.get('executor_name') or client_info.get('executor')
        if executor == 'telegram_executor':
            buttons.append({
                'text': '➕ Создать опрос',
                'callback_data': callback_generator(self.scene.__scene_name__, 'create_poll'),
                'ignore_row': True
            })
            buttons.append({
                'text': '➕ Создать клавиатуру ссылок',
                'callback_data': callback_generator(self.scene.__scene_name__, 'create_keyboard'),
                'ignore_row': True
            })

        task_id = self.scene.data['scene'].get('task_id')
        if task_id:
            entities = [e.to_dict() for e in await Entity.filter_by(card_id=_UUID(str(task_id)), client_key=self.selected_client)]
            if entities:
                for e in entities:
                    eid = e.get('id')
                    title = e.get('data', {}).get('name') or e.get('type') or e.get('type')
                    buttons.append({
                        'text': f'👁 {title}',
                        'callback_data': callback_generator(self.scene.__scene_name__, 'view', eid)
                    })
                    buttons.append({
                        'text': f'🗑',
                        'callback_data': callback_generator(self.scene.__scene_name__, 'delete', eid)
                    })

        return buttons

    @Page.on_callback('switch_client')
    async def switch_client(self, callback, args):
        """Switch between clients"""
        card = await self.scene.get_card_data()
        clients = card.get('clients', []) if card else []
        
        if not clients:
            await callback.answer("❌ Нет доступных каналов")
            return
        
        try:
            idx = clients.index(self.selected_client)
        except (ValueError, TypeError):
            idx = -1
        
        next_idx = (idx + 1) % len(clients)
        self.selected_client = clients[next_idx]
        await self.scene.update_message()

    @Page.on_callback('create_poll')
    async def create_poll(self, callback, args):
        """Go to poll creation page"""
        await self.scene.update_key('entities-main', 'selected_client', self.selected_client)
        await self.scene.update_page('entities-poll-create')

    @Page.on_callback('create_keyboard')
    async def create_keyboard(self, callback, args):
        """Go to keyboard creation page"""
        await self.scene.update_key('entities-main', 'selected_client', self.selected_client)
        await self.scene.update_page('entities-keyboard-create')

    @Page.on_callback('view')
    async def view(self, callback, args):
        """View entity details"""
        if len(args) < 2:
            await callback.answer('❌ Ошибка')
            return

        eid = args[1]
        await self.scene.update_key('entities-main', 'view_entity_id', eid)
        await self.scene.update_key('entities-main', 'selected_client', self.selected_client)
        await self.scene.update_page('entities-view')

    @Page.on_callback('delete')
    async def delete(self, callback, args):
        """Delete entity"""
        if len(args) < 2:
            await callback.answer('❌ Ошибка')
            return
        eid = args[1]
        
        task_id = self.scene.data['scene'].get('task_id')
        if not task_id:
            await callback.answer('❌ Задача не найдена')
            return
        
        ent = await Entity.get_by_id(_UUID(str(eid)))
        ok = False
        if ent:
            await ent.delete()
            ok = True
        
        if ok:
            await callback.answer('✅ Удалено')
            await self.scene.update_message()
        else:
            await callback.answer('❌ Ошибка')

    @Page.on_callback('back')
    async def back(self, callback, args):
        """Back to main task page"""
        await self.scene.update_page('main-page')
        await self.scene.update_message()
