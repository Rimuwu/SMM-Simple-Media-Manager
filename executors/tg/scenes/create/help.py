from tg.oms.models.page import Page
from tg.oms.utils import callback_generator

class HelpPage(Page):

    __page_name__ = 'help'

    # Список тем помощи: заголовок и текст
    TOPICS = [
        {"key": "ai-parse",
            "title": "🤖 AI",
            "text": "Отправьте произвольный текст: AI попытается извлечь название, описание, ТЗ изображения, хештеги и дедлайн. Это поможет быстро заполнить задачу, но требует проверки и доработки."
         },
        {"key": "name",
            "title": "📌 Название",
            "text": "Задайте короткое понятное название задачи (до 100 символов)."
         },
        {"key": "type",
            "title": "🎯 Тип",
            "text": "Свободное — отправляется на форум; Личное — назначается конкретному исполнителю. Если вы не уверены, лучше выбрать 'Свободное'."
         },
        {"key": "description",
            "title": "📄 Описание",
            "text": "Подробное ТЗ для копирайтера. Можно использовать до 2096 знаков. Опишите все важные детали и требования к контенту."
            },
        {"key": "user",
            "title": "👤 Исполнитель",
            "text": "Выберите пользователя, который будет выполнять задачу."
        },
        {"key": "channels",
            "title": "📢 Каналы",
            "text": "Выберите каналы для публикации — можно выбрать несколько."
        },
        {"key": "publish-date",
            "title": "📅 Дедлайн",
            "text": "Дата и время, к которым задача должна быть готова. Указываейте с запасом, чтобы успеть самостоятельно проверить контент и дать правки."
        },
        {"key": "send-date",
            "title": "⏰ Дата отправки",
            "text": "Точная дата и время отправки. Если нужна точная дата публикации, используйте эту опцию."
        },
        {"key": "tags",
            "title": "🏷 Теги",
            "text": "Хештеги для задачи. Используйте, только если понимаете, зачем они нужны."
        },
        {"key": "image",
            "title": "🖼 Изображение",
            "text": "Техническое задание для дизайнеров. Данное сообщение будет отправлено дизайнерам."
        },
        {"key": "files",
            "title": "📎 Файлы",
            "text": "Можно прикреплять фото, документы или видео к задаче."
        },
        {"key": "editor-check",
            "title": "⚙️ Проверка редактором",
            "text": "Если включена, задача требует проверки редактором перед завершением (доступно только админам)."
        },
        {"key": "mode",
            "title": "🧭 Режим",
            "text": "Переключение между Простым и Продвинутым режимами. В простом режиме отображается базовый набор кнопок."
        },
        {"key": "finish",
            "title": "✅ Завершить",
            "text": "Создать задачу с текущими данными."
        },
        {"key": "cancel",
            "title": "❌ Отменить создание",
            "text": "Отменить создание и удалить все введённые данные."
        }
    ]

    async def content_worker(self) -> str:
        """Показываем текущую тему или список тем"""
        self.clear_content()

        idx = self.get_data('index') or 0
        list_view = self.get_data('list_view') or False

        if list_view:
            lines = ["📚 *Список тем помощи:*\n"]
            for i, t in enumerate(self.TOPICS):
                lines.append(f"{i+1}. {t['title']}")
            self.content = "\n".join(lines)
        else:
            # Убедимся, что индекс в пределах
            idx = max(0, min(idx, len(self.TOPICS) - 1))
            t = self.TOPICS[idx]
            self.content = f"**{t['title']}**\n\n{t['text']}\n\n_{idx+1}/{len(self.TOPICS)}_"

        return self.content

    async def buttons_worker(self) -> list[dict]:
        """Навигация: Prev / List / Next + (to_pages добавит '⬅️ Назад')"""
        buttons = []
        idx = self.get_data('index') or 0
        list_view = self.get_data('list_view') or False

        if list_view:
            # Показываем кнопки для каждой темы (по 2 в ряд если нужно)
            for i, t in enumerate(self.TOPICS):
                buttons.append({
                    'text': f"{t['title']}",
                    'callback_data': callback_generator(self.scene.__scene_name__, 'help_topic', str(i))
                })
            # Кнопка закрытия списка
            buttons.append({
                'text': '◀️ Вернуться',
                'callback_data': callback_generator(self.scene.__scene_name__, 'help_close_list')
            })
            return buttons

        # Обычная тема: Prev / List / Next
        buttons.append({
            'text': '⬅️ Назад',
            'callback_data': callback_generator(self.scene.__scene_name__, 'help_prev')
        })
        buttons.append({
            'text': '📚 Список',
            'callback_data': callback_generator(self.scene.__scene_name__, 'help_list')
        })
        buttons.append({
            'text': '➡️ Вперед',
            'callback_data': callback_generator(self.scene.__scene_name__, 'help_next')
        })

        return buttons

    @Page.on_callback('help_next')
    async def help_next(self, callback, args):
        idx = self.get_data('index') or 0
        idx = min(idx + 1, len(self.TOPICS) - 1)
        await self.update_data('index', idx)
        await self.scene.update_message()
        return 'exit'

    @Page.on_callback('help_prev')
    async def help_prev(self, callback, args):
        idx = self.get_data('index') or 0
        idx = max(idx - 1, 0)
        await self.update_data('index', idx)
        await self.scene.update_message()
        return 'exit'

    @Page.on_callback('help_list')
    async def help_list(self, callback, args):
        await self.update_data('list_view', True)
        await self.scene.update_message()
        return 'exit'

    @Page.on_callback('help_close_list')
    async def help_close_list(self, callback, args):
        await self.update_data('list_view', False)
        await self.scene.update_message()
        return 'exit'

    @Page.on_callback('help_topic')
    async def help_topic(self, callback, args):
        # args example: ['help_topic', '3']
        if len(args) >= 2:
            try:
                idx = int(args[1])
            except Exception:
                idx = 0
        else:
            idx = 0
        idx = max(0, min(idx, len(self.TOPICS) - 1))
        await self.update_data('index', idx)
        await self.update_data('list_view', False)
        await self.scene.update_message()
        return 'exit'
