from tg.oms.models.text_page import TextTypeScene
from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.api_client import brain_api


class KeyboardCreatePage(TextTypeScene):
    __page_name__ = 'entities-keyboard-create'
    __scene_key__ = 'keyboard_text_input'

    def __after_init__(self):
        super().__after_init__()
        self.next_page = ''

    async def data_preparate(self):
        """Initialize keyboard data if not exists"""
        page = self.scene.data.get(self.__page_name__, {})
        keyboard_data = page.get('data') if isinstance(page, dict) else None

        # Если данных нет, или они пусты — создаём дефолтную структуру
        if not keyboard_data:
            keyboard_data = {
                'buttons': [],
                'name': 'Клавиатура ссылок',
                'edit_mode': None,
                'edit_button_idx': None
            }
            await self.scene.update_key(self.__page_name__, 'data', keyboard_data)
        else:
            # Обеспечиваем наличие ключей
            keyboard_data.setdefault('buttons', [])
            keyboard_data.setdefault('name', 'Клавиатура ссылок')
            keyboard_data.setdefault('edit_mode', None)
            keyboard_data.setdefault('edit_button_idx', None)

            await self.scene.update_key(self.__page_name__, 'data', keyboard_data)

        # Ensure selected client is set
        selected_client = self.scene.data.get('entities-main', {}).get('selected_client')
        if not selected_client:
            card = await self.scene.get_card_data()
            if card:
                clients = card.get('clients', [])
                if clients:
                    selected_client = clients[0]
                    await self.scene.update_key('entities-main', 'selected_client', selected_client)

    async def content_worker(self) -> str:
        keyboard_data = self.scene.data.get(self.__page_name__, {}).get('data', {})
        edit_mode = self.scene.data.get(self.__page_name__, {}).get('edit_mode')
        text_input = self.scene.data['scene'].get('keyboard_text_input', '').strip()

        if edit_mode == 'name':
            name = keyboard_data.get('name') or 'Клавиатура ссылок'
            return f"✏️ *Редактирование названия*\nТекущее название: {name}\n\nВведите новое название: {text_input}"

        elif edit_mode == 'button_text':
            idx = self.scene.data.get(self.__page_name__, {}).get('edit_button_idx')
            buttons = keyboard_data.get('buttons', [])
            if idx is not None and 0 <= idx < len(buttons):
                current = buttons[idx].get('text', '')
                return f"✏️ *Редактирование текста кнопки {idx + 1}*\n\nТекущий текст: {current}\n\nВведите новый текст: {text_input}"
            return "❌ Кнопка не найдена"

        elif edit_mode == 'button_url':
            idx = self.scene.data.get(self.__page_name__, {}).get('edit_button_idx')
            buttons = keyboard_data.get('buttons', [])
            if idx is not None and 0 <= idx < len(buttons):
                current = buttons[idx].get('url', '')
                style = buttons[idx].get('style') or 'Без стиля'
                return f"🔗 *Редактирование URL кнопки {idx + 1}*\n\nТекущая ссылка: {current}\nТекущий стиль: {style}\n\nВведите новую ссылку: {text_input}"
            return "❌ Кнопка не найдена"

        elif edit_mode == 'button_style':
            idx = self.scene.data.get(self.__page_name__, {}).get('edit_button_idx')
            buttons = keyboard_data.get('buttons', [])
            if idx is not None and 0 <= idx < len(buttons):
                current = buttons[idx].get('style') or 'Без стиля'
                return f"🎨 *Редактирование стиля кнопки {idx + 1}*\n\nТекущий стиль: {current}\n\nВыберите новый стиль:"
            return "❌ Кнопка не найдена"

        elif edit_mode == 'add_button_text':
            return f"✏️ *Добавить кнопку*\n\nВведите текст кнопки: {text_input}"

        elif edit_mode == 'add_button_url':
            return f"🔗 *Добавить кнопку*\n\nВведите URL: {text_input}"

        name = keyboard_data.get('name', 'Клавиатура ссылок')
        buttons = keyboard_data.get('buttons', [])

        content = "⌨️ *Создание клавиатуры ссылок*\n\n"
        content += f"📝 *Название:* {name}\n\n"
        content += "*Кнопки:*\n"
        
        if buttons:
            for i, btn in enumerate(buttons):
                text = btn.get('text', 'Без текста')
                url = btn.get('url', 'Без ссылки')
                style = btn.get('style') or 'Без стиля'
                content += f"{i+1}. {text} → {url} ({style})\n"
        else:
            content += "Нет кнопок"
        
        return self.append_variables(content=content)

    async def buttons_worker(self) -> list[dict]:
        buttons = []
        keyboard_data = self.scene.data.get(self.__page_name__, {}).get('data', {})
        edit_mode = self.scene.data.get(self.__page_name__, {}).get('edit_mode')

        if edit_mode in ('name', 'button_text', 'button_url', 'add_button_text', 'add_button_url'):
            buttons.append({
                'text': '✅ Сохранить',
                'callback_data': callback_generator(self.scene.__scene_name__, 'save_text'),
                'ignore_row': True
            })
            buttons.append({
                'text': '⬅️ К клавиатуре',
                'callback_data': callback_generator(self.scene.__scene_name__, 'cancel_edit'),
                'ignore_row': True
            })
            return buttons

        if edit_mode == 'button_style':
            idx = self.scene.data.get(self.__page_name__, {}).get('edit_button_idx')
            btns = keyboard_data.get('buttons', [])
            if idx is None or not (0 <= idx < len(btns)):
                return buttons
            current = btns[idx].get('style')

            # Варианты стиля
            options = [
                ('primary', '🔵 Primary'),
                ('success', '🟢 Success'),
                ('danger', '🔴 Danger'),
                (None, '➖ Без стиля')
            ]

            for val, label in options:
                label_text = label + (' ✅' if current == val else '')
                cb_val = 'none' if val is None else val

                buttons.append({
                    'text': label_text,
                    'callback_data': callback_generator(
                        self.scene.__scene_name__, 'set_button_style', str(idx), cb_val),
                    'style': val,
                    'ignore_row': val == 'danger'
                })

            buttons.append({
                'text': '⬅️ К клавиатуре',
                'callback_data': callback_generator(self.scene.__scene_name__, 'cancel_edit'),
                'ignore_row': True
            })

            return buttons

        buttons.append({
            'text': '✏️ Название',
            'callback_data': callback_generator(self.scene.__scene_name__, 'edit_name'),
            'ignore_row': True
        })

        buttons.append({
            'text': '➕ Добавить кнопку',
            'callback_data': callback_generator(self.scene.__scene_name__, 'add_button'),
            'ignore_row': True
        })
        
        btn_list = keyboard_data.get('buttons', [])
        for i, btn in enumerate(btn_list):
            text = btn.get('text', 'Без текста')[:18]
            buttons.append({
                'text': f'{i+1}. {text}',
                'callback_data': callback_generator(self.scene.__scene_name__, 'edit_button', str(i)),
                'next_line': True
            })
            buttons.append({
                'text': '🎨',
                'callback_data': callback_generator(self.scene.__scene_name__, 'edit_button_style', str(i))
            })
            buttons.append({
                'text': '🗑',
                'callback_data': callback_generator(self.scene.__scene_name__, 'delete_button', str(i))
            })

        buttons.append({
            'text': '💾 Сохранить клавиатуру',
            'callback_data': callback_generator(self.scene.__scene_name__, 'save_keyboard'),
            'ignore_row': True
        })

        buttons.append({
            'text': '❌ Отмена',
            'callback_data': callback_generator(self.scene.__scene_name__, 'back')
        })

        return buttons

    @Page.on_callback('edit_name')
    async def edit_name(self, callback, args):
        """Switch to name editing mode"""
        await self.scene.update_key(self.__page_name__, 'edit_mode', 'name')
        await self.scene.update_message()

    @Page.on_callback('add_button')
    async def add_button(self, callback, args):
        """Start adding button - first get text"""
        await self.scene.update_key(self.__page_name__, 'edit_mode', 'add_button_text')
        await self.scene.update_message()

    @Page.on_callback('edit_button')
    async def edit_button(self, callback, args):
        """Switch to edit button mode"""
        if len(args) < 2:
            await callback.answer('❌ Ошибка')
            return

        idx = int(args[1])
        await self.scene.update_key(self.__page_name__, 'edit_mode', 'button_text')
        await self.scene.update_key(self.__page_name__, 'edit_button_idx', idx)
        await self.scene.update_message()

    @Page.on_callback('edit_button_style')
    async def edit_button_style(self, callback, args):
        """Switch to edit button style mode"""
        if len(args) < 2:
            await callback.answer('❌ Ошибка')
            return

        idx = int(args[1])
        await self.scene.update_key(self.__page_name__, 'edit_mode', 'button_style')
        await self.scene.update_key(self.__page_name__, 'edit_button_idx', idx)
        await self.scene.update_message()

    @Page.on_callback('set_button_style')
    async def set_button_style(self, callback, args):
        """Set style for a button via callback (args: idx, style)"""
        if len(args) < 3:
            await callback.answer('❌ Ошибка')
            return

        try:
            idx = int(args[1])
        except Exception:
            await callback.answer('❌ Ошибка')
            return

        style_arg = args[2]
        style = style_arg if style_arg in ('primary', 'success', 'danger') else None

        keyboard_data = self.scene.data.get(self.__page_name__, {}).get('data', {})
        buttons = keyboard_data.get('buttons', [])
        if idx is None or not (0 <= idx < len(buttons)):
            await callback.answer('❌ Ошибка')
            return

        buttons[idx]['style'] = style
        keyboard_data['buttons'] = buttons
        await self.scene.update_key(self.__page_name__, 'data', keyboard_data)
        await self.scene.update_key(self.__page_name__, 'edit_mode', None)
        await callback.answer('✅ Стиль кнопки изменён')
        await self.scene.update_message()

    @Page.on_callback('save_text')
    async def save_text(self, callback, args):
        """Save text input based on edit mode"""
        text_input = self.scene.data['scene'].get('keyboard_text_input', '').strip()
        
        if not text_input:
            await callback.answer('❌ Текст не может быть пустым')
            return
        
        keyboard_data = self.scene.data.get(self.__page_name__, {}).get('data', {})
        edit_mode = self.scene.data.get(self.__page_name__, {}).get('edit_mode')
        
        if edit_mode == 'name':
            keyboard_data['name'] = text_input
            await callback.answer('✅ Название установлено')
        
        elif edit_mode == 'add_button_text':
            # Сохраняем текст и переходим к вводу URL
            await self.scene.update_key(self.__page_name__, 'temp_button_text', text_input)
            await self.scene.update_key(self.__page_name__, 'edit_mode', 'add_button_url')
            await self.scene.update_key('scene', 'keyboard_text_input', '')
            await self.scene.update_message()
            return

        elif edit_mode == 'add_button_url':
            # Добавляем кнопку с сохранённым текстом
            temp_text = self.scene.data.get(self.__page_name__, {}).get('temp_button_text')
            buttons = keyboard_data.get('buttons', [])
            # Сохраняем кнопку с полем 'style' (None — без стиля)
            buttons.append({'text': temp_text, 'url': text_input, 'style': None})
            keyboard_data['buttons'] = buttons
            await self.scene.update_key(self.__page_name__, 'temp_button_text', None)
            await callback.answer('✅ Кнопка добавлена')
        
        elif edit_mode == 'button_text':
            idx = self.scene.data.get(self.__page_name__, {}).get('edit_button_idx')
            buttons = keyboard_data.get('buttons', [])
            if idx is not None and 0 <= idx < len(buttons):
                buttons[idx]['text'] = text_input
                keyboard_data['buttons'] = buttons
                await callback.answer('✅ Текст кнопки изменён')
                # Переходим к редактированию URL
                await self.scene.update_key(self.__page_name__, 'edit_mode', 'button_url')
                await self.scene.update_key('scene', 'keyboard_text_input', '')
                await self.scene.update_message()
                return
            else:
                await callback.answer('❌ Ошибка')
                return

        elif edit_mode == 'button_url':
            idx = self.scene.data.get(self.__page_name__, {}).get('edit_button_idx')
            buttons = keyboard_data.get('buttons', [])
            if idx is not None and 0 <= idx < len(buttons):
                buttons[idx]['url'] = text_input
                keyboard_data['buttons'] = buttons
                await callback.answer('✅ URL кнопки изменён')
            else:
                await callback.answer('❌ Ошибка')
                return
        
        await self.scene.update_key(self.__page_name__, 'data', keyboard_data)
        await self.scene.update_key(self.__page_name__, 'edit_mode', None)
        await self.scene.update_key('scene', 'keyboard_text_input', '')
        await self.scene.update_message()

    @Page.on_callback('cancel_edit')
    async def cancel_edit(self, callback, args):
        """Cancel editing"""
        await self.scene.update_key(self.__page_name__, 'edit_mode', None)
        await self.scene.update_key(self.__page_name__, 'temp_button_text', None)
        await self.scene.update_key('scene', 'keyboard_text_input', '')
        await self.scene.update_message()

    @Page.on_callback('delete_button')
    async def delete_button(self, callback, args):
        """Delete button at index"""
        if len(args) < 2:
            await callback.answer('❌ Ошибка')
            return

        idx = int(args[1])
        keyboard_data = self.scene.data.get(self.__page_name__, {}).get('data', {})
        buttons = keyboard_data.get('buttons', [])

        if 0 <= idx < len(buttons):
            buttons.pop(idx)
            await self.scene.update_key(self.__page_name__, 'data', keyboard_data)
            await callback.answer('✅ Кнопка удалена')
            await self.scene.update_message()
        else:
            await callback.answer('❌ Ошибка')

    @Page.on_callback('back')
    async def back(self, callback, args):
        await self.scene.update_page('entities-main')

    @Page.on_callback('save_keyboard')
    async def save_keyboard(self, callback, args):
        """Save keyboard to database"""
        keyboard_data = self.scene.data.get(self.__page_name__, {}).get('data', {})

        buttons = keyboard_data.get('buttons', [])
        if len(buttons) < 1:
            await callback.answer('❌ Добавьте хотя бы одну кнопку')
            return
        
        task_id = self.scene.data['scene'].get('task_id')
        if not task_id:
            await callback.answer('❌ Задача не найдена')
            return

        selected_client = self.scene.data.get('entities-main', {}).get('selected_client')
        if not selected_client:
            await callback.answer('❌ Клиент не выбран')
            return
        
        payload = {
            'card_id': task_id,
            'client_id': selected_client,
            'entity_type': 'inline_keyboard',
            'data': {
                'buttons': buttons,
                'name': keyboard_data.get('name', 'Клавиатура ссылок')
            },
            'name': keyboard_data.get('name', 'Клавиатура ссылок')[:50]
        }

        # Если установлен entity_id - обновляем сущность вместо создания новой
        entity_id = self.scene.data.get(self.__page_name__, {}).get('entity_id')
        if entity_id:
            up_payload = {
                'card_id': task_id,
                'client_id': selected_client,
                'entity_id': entity_id,
                'data': payload['data'],
                'name': payload.get('name')
            }

            resp, status = await brain_api.post('/card/update-entity', data=up_payload)
            if status == 200 and resp:
                await self.scene.update_key(self.__page_name__, 'data', {})
                await self.scene.update_key(self.__page_name__, 'entity_id', None)
                await self.scene.update_page('entities-main')
                await callback.answer('✅ Клавиатура обновлена')
            else:
                await callback.answer(f'❌ Ошибка обновления {resp.get("detail", "")}', show_alert=True)
            return

        # Создание новой сущности
        resp, status = await brain_api.post('/card/add-entity', data=payload)
        if status == 200 and resp:
            await self.scene.update_key(self.__page_name__, 'data', {})
            await self.scene.update_page('entities-main')
            await callback.answer('✅ Клавиатура создана')
        else:
            await callback.answer('❌ Ошибка создания')
