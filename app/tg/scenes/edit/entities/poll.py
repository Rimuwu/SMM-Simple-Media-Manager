from tg.oms.models.text_page import TextTypeScene
from tg.oms import Page
from tg.oms.utils import callback_generator
from models.Entity import Entity
from uuid import UUID as _UUID
from datetime import datetime


class PollCreatePage(TextTypeScene):
    __page_name__ = 'entities-poll-create'
    __scene_key__ = 'poll_text_input'

    def __after_init__(self):
        super().__after_init__()
        self.next_page = ''

    async def data_preparate(self):
        """Initialize poll data if not exists"""
        page = self.scene.data.get(self.__page_name__, {})
        poll_data = page.get('data') if isinstance(page, dict) else None

        # Если данных нет, или они пусты — создаём дефолтную структуру
        if not poll_data:
            poll_data = {
                'question': None,
                'options': [],
                'type': 'regular',
                'allows_multiple_answers': False,
                'correct_option_id': None,
                'explanation': None,
                'edit_mode': None,
                'edit_option_idx': None
            }
            await self.scene.update_key(self.__page_name__, 'data', poll_data)
        else:
            # Обеспечиваем наличие ключей в случае редактирования существующей сущности
            poll_data.setdefault('question', None)
            poll_data.setdefault('options', [])
            poll_data.setdefault('type', 'regular')
            poll_data.setdefault('allows_multiple_answers', False)
            poll_data.setdefault('correct_option_id', None)
            poll_data.setdefault('explanation', None)
            poll_data.setdefault('edit_mode', None)
            poll_data.setdefault('edit_option_idx', None)
            await self.scene.update_key(self.__page_name__, 'data', poll_data)
        
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
        poll_data = self.scene.data.get(self.__page_name__, {}).get('data', {})
        edit_mode = self.scene.data.get(self.__page_name__, {}).get('edit_mode')
        text_input = self.scene.data['scene'].get('poll_text_input', '').strip()

        if edit_mode == 'question':
            question = poll_data.get('question') or 'Не установлен'
            return f"✏️ *Редактирование вопроса*\nТекущий вопрос: {question}\n\nВведите новый вопрос: {text_input}"

        elif edit_mode == 'add_option':
            return f"➕ *Добавить вариант ответа*\n\nВведите новый вариант: {text_input}"

        elif edit_mode == 'edit_option':
            idx = self.scene.data.get(self.__page_name__, {}).get('edit_option_idx')
            options = poll_data.get('options', [])

            if idx is not None and 0 <= idx < len(options):
                current = options[idx]
                return f"✏️ *Редактирование варианта {idx + 1}*\n\nТекущий текст: {current}\n\nВведите новый текст: {text_input}"
            return "❌ Вариант не найден"
        
        elif edit_mode == 'explanation':
            explanation = poll_data.get('explanation') or 'Не установлено'
            return f"💬 *Редактирование объяснения*\n\nТекущее объяснение: {explanation}\n\nВведите новое объяснение: {text_input}"

        question = poll_data.get('question') or 'Вопрос не установлен'
        poll_type = poll_data.get('type', 'regular')
        allows_multiple = poll_data.get('allows_multiple_answers', False)
        explanation = poll_data.get('explanation')
        correct_option = poll_data.get('correct_option_id')
        
        options = poll_data.get('options', [])
        if options:
            options_text = '\n'.join(f"{i+1}. {opt}" for i, opt in enumerate(options))
        else:
            options_text = 'Нет вариантов'

        content = "🗳 *Создание опроса*\n\n"
        content += f"❓ *Вопрос:* {question}\n\n"
        content += "*Варианты ответов:*\n"
        content += options_text + "\n\n"
        content += "⚙️ *Настройки:*\n"
        content += f"• Тип: {'Опрос' if poll_type == 'regular' else 'Викторина'}\n"
        content += f"• Несколько ответов: {'✅' if allows_multiple else '❌'}\n"
        
        if poll_type == 'quiz' and correct_option is not None:
            content += f"• Правильный ответ: вариант {correct_option + 1}\n"
        
        if explanation:
            content += f"• Объяснение: {explanation}\n"
        
        return content

    async def buttons_worker(self) -> list[dict]:
        buttons = []
        poll_data = self.scene.data.get(self.__page_name__, {}).get('data', {})
        edit_mode = self.scene.data.get(self.__page_name__, {}).get('edit_mode')

        if edit_mode:
            buttons.append({
                'text': '✅ Сохранить',
                'callback_data': callback_generator(self.scene.__scene_name__, 'save_text'),
                'ignore_row': True
            })
            buttons.append({
                'text': '⬅️ К опросу',
                'callback_data': callback_generator(self.scene.__scene_name__, 'cancel_edit'),
                'ignore_row': True
            })
            return buttons

        buttons.append({
            'text': '✏️ Вопрос',
            'callback_data': callback_generator(self.scene.__scene_name__, 'edit_question'),
        })
        
        buttons.append({
            'text': '⚙️ Настройки',
            'callback_data': callback_generator(self.scene.__scene_name__, 'settings'),
        })

        poll_type = poll_data.get('type', 'regular')
        if poll_type == 'quiz':
            buttons.append({
                'text': '🎯 Правильный ответ',
                'callback_data': callback_generator(self.scene.__scene_name__, 'set_correct_answer'),
                'next_line': True
            })
            buttons.append({
                'text': '💬 Объяснение',
                'callback_data': callback_generator(self.scene.__scene_name__, 'edit_explanation')
            })

        buttons.append({
            'text': '➕ Добавить вариант',
            'callback_data': callback_generator(self.scene.__scene_name__, 'add_option'),
            'ignore_row': True
        })
        
        options = poll_data.get('options', [])
        for i, opt in enumerate(options):
            buttons.append({
                'text': f'{opt[:20]}',
                'callback_data': callback_generator(self.scene.__scene_name__, 'edit_option', str(i)),
                'next_line': True
            })
            buttons.append({
                'text': '🗑',
                'callback_data': callback_generator(self.scene.__scene_name__, 'delete_option', str(i))
            })
            
            if i > 0:
                buttons.append({
                    'text': '⬆️',
                    'callback_data': callback_generator(self.scene.__scene_name__, 'move_up', str(i))
                })

            if i < len(options) - 1:
                buttons.append({
                    'text': '⬇️',
                    'callback_data': callback_generator(self.scene.__scene_name__, 'move_down', str(i))
                })

        buttons.append({
            'text': '💾 Сохранить опрос',
            'callback_data': callback_generator(self.scene.__scene_name__, 'save_poll'),
            'ignore_row': True
        })

        buttons.append({
            'text': '❌ Отмена',
            'callback_data': callback_generator(self.scene.__scene_name__, 'back')
        })

        return buttons

    @Page.on_callback('edit_question')
    async def edit_question(self, callback, args):
        """Switch to question editing mode"""
        await self.scene.update_key(self.__page_name__, 'edit_mode', 'question')
        await self.scene.update_message()

    @Page.on_callback('add_option')
    async def add_option(self, callback, args):
        """Switch to add option mode"""
        await self.scene.update_key(self.__page_name__, 'edit_mode', 'add_option')
        await self.scene.update_message()

    @Page.on_callback('edit_option')
    async def edit_option(self, callback, args):
        """Switch to edit option mode"""
        if len(args) < 2:
            await callback.answer('❌ Ошибка')
            return
        idx = int(args[1])
        await self.scene.update_key(self.__page_name__, 'edit_mode', 'edit_option')
        await self.scene.update_key(self.__page_name__, 'edit_option_idx', idx)
        await self.scene.update_message()

    @Page.on_callback('save_text')
    async def save_text(self, callback, args):
        """Save text input based on edit mode"""
        text_input = self.scene.data['scene'].get('poll_text_input', '').strip()
        
        if not text_input:
            await callback.answer('❌ Текст не может быть пустым')
            return
        
        poll_data = self.scene.data.get(self.__page_name__, {}).get('data', {})
        edit_mode = self.scene.data.get(self.__page_name__, {}).get('edit_mode')
        
        if edit_mode == 'question':
            poll_data['question'] = text_input
            await callback.answer('✅ Вопрос установлен')
        
        elif edit_mode == 'add_option':
            options = poll_data.get('options', [])
            options.append(text_input)
            poll_data['options'] = options
            await callback.answer('✅ Вариант добавлен')
        
        elif edit_mode == 'edit_option':
            idx = self.scene.data.get(self.__page_name__, {}).get('edit_option_idx')
            options = poll_data.get('options', [])
            if idx is not None and 0 <= idx < len(options):
                options[idx] = text_input
                poll_data['options'] = options
                await callback.answer('✅ Вариант изменён')
            else:
                await callback.answer('❌ Ошибка')
                return
        
        elif edit_mode == 'explanation':
            poll_data['explanation'] = text_input
            await callback.answer('✅ Объяснение установлено')
        
        await self.scene.update_key(self.__page_name__, 'data', poll_data)
        await self.scene.update_key(self.__page_name__, 'edit_mode', None)
        await self.scene.update_key('scene', 'poll_text_input', '')
        await self.scene.update_message()

    @Page.on_callback('cancel_edit')
    async def cancel_edit(self, callback, args):
        """Cancel editing"""
        await self.scene.update_key(self.__page_name__, 'edit_mode', None)
        await self.scene.update_key('scene', 'poll_text_input', '')
        await self.scene.update_message()

    @Page.on_callback('delete_option')
    async def delete_option(self, callback, args):
        """Delete option at index"""
        if len(args) < 2:
            await callback.answer('❌ Ошибка')
            return

        idx = int(args[1])
        poll_data = self.scene.data.get(self.__page_name__, {}).get('data', {})
        options = poll_data.get('options', [])

        if 0 <= idx < len(options):
            options.pop(idx)
            await self.scene.update_key(self.__page_name__, 'data', poll_data)
            await callback.answer('✅ Вариант удалён')
            await self.scene.update_message()
        else:
            await callback.answer('❌ Ошибка')

    @Page.on_callback('move_up')
    async def move_up(self, callback, args):
        """Move option up"""
        if len(args) < 2:
            await callback.answer('❌ Ошибка')
            return

        idx = int(args[1])
        poll_data = self.scene.data.get(self.__page_name__, {}).get('data', {})
        options = poll_data.get('options', [])

        if idx > 0 and idx < len(options):
            options[idx-1], options[idx] = options[idx], options[idx-1]
            await self.scene.update_key(self.__page_name__, 'data', poll_data)
            await callback.answer('✅ Перемещено')
            await self.scene.update_message()
        else:
            await callback.answer('❌ Ошибка')

    @Page.on_callback('move_down')
    async def move_down(self, callback, args):
        """Move option down"""
        if len(args) < 2:
            await callback.answer('❌ Ошибка')
            return

        idx = int(args[1])
        poll_data = self.scene.data.get(self.__page_name__, {}).get('data', {})
        options = poll_data.get('options', [])

        if idx >= 0 and idx < len(options) - 1:
            options[idx], options[idx+1] = options[idx+1], options[idx]
            await self.scene.update_key(self.__page_name__, 'data', poll_data)
            await callback.answer('✅ Перемещено')
            await self.scene.update_message()
        else:
            await callback.answer('❌ Ошибка')

    @Page.on_callback('settings')
    async def settings(self, callback, args):
        """Show settings options"""
        poll_data = self.scene.data.get(self.__page_name__, {}).get('data', {})

        poll_type = poll_data.get('type', 'regular')
        allows_multi = poll_data.get('allows_multiple_answers', False)

        settings_text = (f"⚙️ <b>Настройки опроса</b>\n"
                         f"• <b>Тип:</b> {'Опрос' if poll_type == 'regular' else 'Викторина'}\n"
                         )

        keyboard = [
            [{'text': '📊 Тип опроса',
              'callback_data':
                  callback_generator(self.scene.__scene_name__, 'toggle_type')}],
            [{'text': '⬅️ Назад',
              'callback_data':
                  callback_generator(self.scene.__scene_name__, 'back_to_main')}]
        ]

        if poll_type == 'regular':
            settings_text += f"• <b>Несколько ответов:</b> {'✅ Да' if allows_multi else '❌ Нет'}"
            keyboard.insert(1, [{
                'text': '☑️ Несколько ответов',
                'callback_data':
                    callback_generator(self.scene.__scene_name__, 'toggle_multiple')}]
            )

        await callback.message.edit_text(
            settings_text, reply_markup={'inline_keyboard': keyboard}, parse_mode='html')

    @Page.on_callback('toggle_type')
    async def toggle_type(self, callback, args):
        """Toggle between regular and quiz"""
        poll_data = self.scene.data.get(self.__page_name__, {}).get('data', {})
        current_type = poll_data.get('type', 'regular')
        poll_data['type'] = 'quiz' if current_type == 'regular' else 'regular'

        if poll_data['type'] == 'regular':
            poll_data['correct_option_id'] = None
            poll_data['explanation'] = None

        elif poll_data['type'] == 'quiz':
            poll_data['allows_multiple_answers'] = None

        await self.scene.update_key(self.__page_name__, 'data', poll_data)
        await self.settings(callback, args)

    @Page.on_callback('toggle_multiple')
    async def toggle_multiple(self, callback, args):
        """Toggle multiple answers"""
        poll_data = self.scene.data.get(self.__page_name__, {}).get('data', {})
        poll_data['allows_multiple_answers'] = not poll_data.get(
            'allows_multiple_answers', False)

        await self.scene.update_key(self.__page_name__, 'data', poll_data)
        await self.settings(callback, args)

    @Page.on_callback('set_correct_answer')
    async def set_correct_answer(self, callback, args):
        """Set correct answer for quiz"""
        poll_data = self.scene.data.get(self.__page_name__, {}).get('data', {})
        options = poll_data.get('options', [])

        if not options:
            await callback.answer('❌ Нет вариантов ответов')
            return

        keyboard = [
            [{'text': f'{i+1}. {opt[:20]}',
              'callback_data': callback_generator(self.scene.__scene_name__, 'select_correct', str(i))
              }]
            for i, opt in enumerate(options)
        ]
        keyboard.append([
            {'text': '⬅️ Назад',
             'callback_data': callback_generator(self.scene.__scene_name__, 'back_to_main')
             }]
        )

        await callback.message.edit_text('🎯 <b>Выберите правильный ответ:</b>', reply_markup={'inline_keyboard': keyboard}, parse_mode='html')

    @Page.on_callback('select_correct')
    async def select_correct(self, callback, args):
        """Select correct answer"""
        if len(args) < 2:
            await callback.answer('❌ Ошибка')
            return

        idx = int(args[1])
        poll_data = self.scene.data.get(self.__page_name__, {}).get('data', {})
        poll_data['correct_option_id'] = idx
        await self.scene.update_key(self.__page_name__, 'data', poll_data)
        await callback.answer(f'✅ Правильный ответ установлен: вариант {idx+1}')
        await self.scene.update_message()

    @Page.on_callback('edit_explanation')
    async def edit_explanation(self, callback, args):
        """Switch to explanation editing mode"""
        await self.scene.update_key(self.__page_name__, 'edit_mode', 'explanation')
        await self.scene.update_message()

    @Page.on_callback('back_to_main')
    async def back_to_main(self, callback, args):
        """Back to main poll page"""
        await self.scene.update_message()

    @Page.on_callback('back')
    async def back(self, callback, args):
        await self.scene.update_page('entities-main')

    @Page.on_callback('save_poll')
    async def save_poll(self, callback, args):
        """Save poll to database"""
        poll_data = self.scene.data.get(self.__page_name__, {}).get('data', {})

        if not poll_data.get('question'):
            await callback.answer('❌ Установите вопрос')
            return
        
        if len(poll_data.get('options', [])) < 2:
            await callback.answer('❌ Минимум 2 варианта ответа')
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
            'entity_type': 'poll',
            'data': {
                'question': poll_data['question'],
                'options': poll_data['options'],
                'type': poll_data.get('type', 'regular'),
                'allows_multiple_answers': poll_data.get('allows_multiple_answers', False),
            },
            'name': poll_data['question'][:50]
        }

        if poll_data.get('type') == 'quiz':
            if poll_data.get('correct_option_id') is not None:
                payload['data']['correct_option_id'] = poll_data['correct_option_id']
            if poll_data.get('explanation'):
                payload['data']['explanation'] = poll_data['explanation']

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

            ent = await Entity.get_by_id(_UUID(str(entity_id)))
            result = None
            if ent:
                updated = ent.data.copy() if ent.data else {}
                updated.update(up_payload['data'])
                updated['updated_at'] = datetime.now().isoformat()
                await ent.update(data=updated)
                result = ent.to_dict()
            if result:
                # Очистим режим редактирования
                await self.scene.update_key(self.__page_name__, 'data', {})
                await self.scene.update_key(self.__page_name__, 'entity_id', None)
                await self.scene.update_page('entities-main')
                await callback.answer('✅ Опрос обновлён')
            else:
                await callback.answer('❌ Ошибка обновления опроса')
            return

        # Создание новой сущности
        result = await Entity.create(
            card_id=_UUID(str(task_id)), client_key=selected_client,
            type='poll',
            data=payload['data']
        )
        if result:
            await self.scene.update_key(self.__page_name__, 'data', {})
            await self.scene.update_page('entities-main')
            await callback.answer('✅ Опрос создан')
        else:
            if status == 414:
                await callback.answer('❌ Не указан правильный ответ для викторины')
            await callback.answer('❌ Ошибка создания опроса')