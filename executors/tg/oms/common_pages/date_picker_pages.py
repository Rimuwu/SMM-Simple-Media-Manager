from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.api_client import brain_api
from datetime import datetime, timedelta
import calendar


class DatePickerPage(Page):
    __page_name__ = 'date-picker'

    def __after_init__(self):
        # Локальный кэш для уменьшения количества запросов и вычислений
        # Ключи: month -> (y,m), busy_month -> set(datetime), weeks -> list, 
        # busy_day -> set(datetime), busy_day_date -> 'YYYY-MM-DD',
        # busy_minutes -> set(int), busy_hour -> (date_iso, hour), now/min_delta
        self._cache: dict = {}

    async def page_enter(self, **kwargs) -> None:
        return await super().page_enter(**kwargs)

    async def data_preparate(self) -> None:
        ym = self.scene.get_key(self.__page_name__, 'year_month')
        if not ym:
            now = datetime.now()
            await self.scene.update_key(self.__page_name__, 'year_month', (now.year, now.month))

        # Подготовим и закешируем данные, чтобы buttons_worker работал быстрее
        picker_meta = self.scene.data['scene'].get('date_picker', {})
        min_delta = picker_meta.get('min_delta_seconds', 60)
        now = datetime.now()
        check_busy = picker_meta.get('check_busy_slots', True)

        min_delta = self._cache.get('min_delta', min_delta)
        now = self._cache.get('now', now)
        self._cache['now'] = now
        self._cache['min_delta'] = min_delta

        # Состояние выбора
        sel = self.scene.get_key(self.__page_name__, 'selected_date')
        hour_sel = self.scene.get_key(self.__page_name__, 'selected_hour')

        # Кэш для вида календаря (месяц)
        if not sel:
            year, month = self.scene.get_key(self.__page_name__, 'year_month')
            month_key = (year, month, check_busy)
            if self._cache.get('month') != month_key:
                first_day = datetime(year, month, 1)
                last_day_num = calendar.monthrange(year, month)[1]
                last_day = datetime(year, month, last_day_num, 23, 59, 59)

                busy = set()
                if check_busy:
                    res, status = await brain_api.get('/time/busy-slots', params={'start': first_day.isoformat(), 'end': last_day.isoformat()})
                    if status == 200 and isinstance(res, dict):
                        for item in res.get('busy_slots', []):
                            try:
                                busy_dt = datetime.fromisoformat(item['send_time'])
                                busy.add(busy_dt)
                            except Exception:
                                pass

                cal = calendar.Calendar()
                weeks = list(cal.monthdayscalendar(year, month))

                self._cache['month'] = month_key
                self._cache['busy_month'] = busy
                self._cache['weeks'] = weeks
                self._cache['last_day_num'] = last_day_num

        elif sel and hour_sel is None:
            # Если дата изменилась, пересчитаем
            if self._cache.get('busy_day_date') != (sel, check_busy):
                day_dt = datetime.fromisoformat(sel)
                start = datetime(day_dt.year, day_dt.month, day_dt.day, 0, 0, 0)
                end = datetime(day_dt.year, day_dt.month, day_dt.day, 23, 59, 59)
                busy_day = set()
                if check_busy:
                    res2, status2 = await brain_api.get('/time/busy-slots', params={'start': start.isoformat(), 'end': end.isoformat()})
                    if status2 == 200 and isinstance(res2, dict):
                        for item in res2.get('busy_slots', []):
                            try:
                                busy_dt = datetime.fromisoformat(item['send_time'])
                                busy_day.add(busy_dt)
                            except Exception:
                                pass

                self._cache['busy_day_date'] = (sel, check_busy)
                self._cache['busy_day'] = busy_day

        # Кэш для минут (busy for hour)
        elif sel and hour_sel is not None:
            cache_tag = (sel, hour_sel)
            if self._cache.get('busy_hour') != (cache_tag, check_busy):
                day_dt = datetime.fromisoformat(sel)
                start_h = datetime(day_dt.year, day_dt.month, day_dt.day, hour_sel, 0)
                end_h = datetime(day_dt.year, day_dt.month, day_dt.day, hour_sel, 59, 59)
                busy_minutes = set()
                if check_busy:
                    res3, status3 = await brain_api.get('/time/busy-slots', params={'start': start_h.isoformat(), 'end': end_h.isoformat()})
                    if status3 == 200 and isinstance(res3, dict):
                        for item in res3.get('busy_slots', []):
                            try:
                                busy_dt = datetime.fromisoformat(item['send_time'])
                                busy_minutes.add(busy_dt.minute)
                            except Exception:
                                pass

                self._cache['busy_hour'] = (cache_tag, check_busy)
                self._cache['busy_minutes'] = busy_minutes

    async def content_worker(self) -> str:
        content = self.__page__.content

        sel = self.scene.get_key(self.__page_name__, 'selected_date')
        hour = self.scene.get_key(self.__page_name__, 'selected_hour')
        if sel:
            try:
                dt = datetime.fromisoformat(sel)
                header = f"Просматривается дата: {dt.strftime('%d.%m.%Y')}\n\n"
            except Exception:
                header = "📅 Выбранная дата\n\n"
        else:
            ym = self.scene.get_key(self.__page_name__, 'year_month')
            year, month = ym
            header = f"Просматривается дата: {year}-{month:02d}\n\n"

        # Легенда для значков
        legend = (
            "❌ — время прошло\n"
            "⭕ — время занято\n"
            "⬜ — весь час / день занят\n\n"
        )

        if hour is not None:
            info = "Выберите точное время (минуты):"
        elif sel:
            info = "Выберите час:"
        else:
            info = "Выберите день:"

        self.content = content + header + legend + info
        return self.content

    async def buttons_worker(self) -> list[dict]:
        """Show either calendar, or hours, or minutes depending on selection stage."""
        buttons = []
        ym = self.scene.get_key(self.__page_name__, 'year_month')
        year, month = ym

        picker_meta = self.scene.data['scene'].get('date_picker', {})
        min_delta = picker_meta.get('min_delta_seconds', 60)
        now = datetime.now()

        # If no date selected -> show calendar only
        sel = self.scene.get_key(self.__page_name__, 'selected_date')
        if not sel:
            # Используем предвычисленные данные из data_preparate
            busy = self._cache.get('busy_month', set())
            weeks = self._cache.get('weeks')
            if weeks is None:
                cal = calendar.Calendar()
                weeks = list(cal.monthdayscalendar(year, month))

            # show calendar grid
            self.row_width = 7
            for week in weeks:
                for day in week:
                    if day == 0:
                        buttons.append({
                            'text': ' ',
                            'callback_data': ' '
                        })
                        continue

                    day_dt = datetime(year, month, day)
                    day_end = datetime(year, month, day, 23, 59, 59)

                    # determine fullness
                    full_day = True
                    for hour in range(0, 24):
                        hour_busy_count = sum(1 for dt in busy if dt.date() == day_dt.date() and dt.hour == hour)
                        if hour_busy_count < 60:
                            full_day = False
                            break

                    if day_end < (now + timedelta(seconds=min_delta)):
                        buttons.append({
                            'text': f'❌ {day}',
                            'callback_data': ' '
                        })
                    elif full_day:
                        buttons.append({
                            'text': f'⭕ {day}',
                            'callback_data': ' '
                        })
                    else:
                        buttons.append({
                            'text': f'{day}',
                            'callback_data': callback_generator(self.scene.__scene_name__, 'pick_date', f"{year}-{month:02d}-{day:02d}")
                        })

            back_page = self.get_data('back_page') or 'main'
            buttons.append({
                'text': '⬅️',
                'callback_data': callback_generator(self.scene.__scene_name__, 'prev_month')
            })
            buttons.append({
                'text': f'{datetime.now().date()}',
                'callback_data': callback_generator(self.scene.__scene_name__, 'now')
            })
            buttons.append({
                'text': '➡️',
                'callback_data': callback_generator(self.scene.__scene_name__, 'next_month')
            })
            buttons.append({
                'text': '⬅️ Назад',
                'callback_data': callback_generator(
                        self.scene.__scene_name__, 
                        'to_page', back_page
                    ),
                'ignore_row': True
            })

            return buttons

        hour_sel = self.scene.get_key(self.__page_name__, 'selected_hour')
        if sel and hour_sel is None:
            self.row_width = 4

            buttons.append({
                'text': f'Выбрано: {sel}',
                'callback_data': ' ',
                'ignore_row': True
            })

            # Используем кэш для занятости дня
            busy_day = self._cache.get('busy_day', set())
            # day_dt требуется для построения часов
            day_dt = datetime.fromisoformat(sel)

            for hour in range(0, 24):
                hour_start = datetime(day_dt.year, day_dt.month, day_dt.day, hour, 0)
                hour_busy = sum(1 for dt in busy_day if dt.hour == hour)
                full_hour = hour_busy >= 60

                if hour_start < (now + timedelta(seconds=min_delta)):
                    buttons.append({
                        'text': f'❌ {hour:02d}',
                        'callback_data': ' '
                    })
                elif full_hour:
                    buttons.append({
                        'text': f'⬜ {hour:02d}',
                        'callback_data': ' '
                    })
                else:
                    buttons.append({
                        'text': f'{hour:02d}',
                        'callback_data': callback_generator(self.scene.__scene_name__, 'pick_hour', str(hour))
                    })

            buttons.append({
                'text': '⬅️ Календарь',
                'callback_data': callback_generator(self.scene.__scene_name__, 'to_calendar'),
                'ignore_row': True
            })
            return buttons

        if sel and hour_sel is not None:

            buttons.append({
                'text': f'Час: {hour_sel:02d}',
                'callback_data': ' ',
                'ignore_row': True
            })

            # Используем кэш для занятости минут
            busy_minutes = self._cache.get('busy_minutes', set())
            # day_dt требуется для построения минут
            day_dt = datetime.fromisoformat(sel)

            step = 5
            available_found = False
            for m in range(0, 60, step):
                candidate = datetime(day_dt.year, day_dt.month, day_dt.day, hour_sel, m)
                if candidate < (now + timedelta(seconds=min_delta)):
                    buttons.append({
                        'text': f'⬜ {m:02d}',
                        'callback_data': ' '
                    })
                elif m in busy_minutes:
                    buttons.append({
                        'text': f'🚫 {m:02d}',
                        'callback_data': ' '
                    })
                else:
                    buttons.append({
                        'text': f'{m:02d}',
                        'callback_data': callback_generator(self.scene.__scene_name__, 'pick_minute', str(m))
                    })
                    available_found = True

            if not available_found:
                buttons.append({
                    'text': '🚫 Нет доступных минут',
                    'callback_data': ' ',
                    'ignore_row': True
                })


            buttons.append({
                'text': '⬅️ Часы',
                'callback_data': callback_generator(self.scene.__scene_name__, 'to_hours'),
                'ignore_row': True
            })
            return buttons

    @Page.on_callback('to_hours')
    async def to_hours(self, callback, args):
        """Вернуться на выбор часов (удалить выбранную минуту)"""
        await self.scene.update_key(self.__page_name__, 'selected_hour', None)
        # очистим кэш чтобы данные пересчитались
        self._cache.clear()
        await callback.answer()
        await self.scene.update_message()

    @Page.on_callback('to_calendar')
    async def to_calendar(self, callback, args):
        """Вернуться на календарь (сбросить выбор даты/часа)"""
        await self.scene.update_key(self.__page_name__, 'selected_date', None)
        await self.scene.update_key(self.__page_name__, 'selected_hour', None)
        # очистим кэш чтобы данные пересчитались
        self._cache.clear()
        await callback.answer()
        await self.scene.update_message()

    @Page.on_callback('prev_month')
    async def prev_month(self, callback, args):
        year, month = self.scene.get_key(self.__page_name__, 'year_month')
        if month == 1:
            year -= 1
            month = 12
        else:
            month -= 1
        await self.scene.update_key(self.__page_name__, 'year_month', (year, month))
        # сбросим кэш месяца
        self._cache.clear()
        await self.scene.update_message()
    
    @Page.on_callback('now')
    async def now_b(self, callback, args):
        month = datetime.now().month
        year = datetime.now().year

        await self.scene.update_key(self.__page_name__, 'year_month', (year, month))
        # сбросим кэш месяца
        self._cache.clear()
        await self.scene.update_message()

    @Page.on_callback('next_month')
    async def next_month(self, callback, args):
        year, month = self.scene.get_key(self.__page_name__, 'year_month')
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        await self.scene.update_key(self.__page_name__, 'year_month', (year, month))
        # сбросим кэш месяца
        self._cache.clear()
        await self.scene.update_message()

    @Page.on_callback('pick_date')
    async def pick_date(self, callback, args):
        if len(args) < 2:
            await callback.answer('❌ Ошибка')
            return
        selected = args[1]
        await self.scene.update_key(self.__page_name__, 'selected_date', selected)
        # дата изменилась — очистим кэш
        self._cache.clear()
        await self.scene.update_message()

    @Page.on_callback('pick_hour')
    async def pick_hour(self, callback, args):
        if len(args) < 2:
            await callback.answer('❌ Ошибка')
            return
        hour = int(args[1])
        await self.scene.update_key(self.__page_name__, 'selected_hour', hour)
        # час изменился — очистим кэш
        self._cache.clear()
        await self.scene.update_message()

    @Page.on_callback('pick_minute')
    async def pick_minute(self, callback, args):
        if len(args) < 2:
            await callback.answer('❌ Ошибка')
            return
        minute = int(args[1])

        sel = self.scene.get_key('date-picker', 'selected_date')
        hour = self.scene.get_key('date-picker', 'selected_hour')
        if not sel or hour is None:
            await callback.answer('❌ Дата или час не выбраны')
            return

        day_dt = datetime.fromisoformat(sel)
        chosen = datetime(day_dt.year, day_dt.month, day_dt.day, hour, minute)

        # Проверяем минимальную границу
        picker_meta = self.scene.data['scene'].get('date_picker', {})
        min_delta = picker_meta.get('min_delta_seconds', 60)
        if chosen < (datetime.now() + timedelta(seconds=min_delta)):
            await callback.answer('❌ Нельзя выбрать прошедшее время')
            return

        # Записываем выбор в целевой ключ сцены
        target_key = picker_meta.get('target_key')
        if not target_key:
            await callback.answer('❌ Ошибка целевого ключа')
            return

        await self.scene.update_key('scene', target_key, chosen.isoformat())

        # Если страницу нужно обновить в БД, попробуем вызвать update_to_database у исходной страницы
        origin_page = self.scene.data['scene'].get('last_page')
        try:
            page_obj = self.scene.get_page(origin_page)
            if hasattr(page_obj, 'update_to_database') and getattr(page_obj, 'update_to_db', False):
                success = await page_obj.update_to_database(chosen)
                if not success:
                    await callback.answer('❌ Ошибка при сохранении в БД')
                    return
        except Exception:
            # Игнорируем ошибки — данные уже записаны в сцену
            pass

        # Возвращаемся на исходную страницу
        await callback.answer('✅ Выбрано')

        self._cache.clear()
        await self.scene.update_key(self.__page_name__, 'selected_date', None)
        await self.scene.update_key(self.__page_name__, 'selected_hour', None)

        await self.scene.update_page(origin_page or self.scene.start_page)