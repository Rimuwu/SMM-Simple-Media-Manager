
from pprint import pprint
from modules.kaiten import kaiten
from modules.json_get import open_settings
import json
from modules.logs import brain_logger as logger
from typing import Dict, List, Any, Optional
import asyncio


async def sync_kaiten_settings():
    """
    Синхронизирует настройки из settings.json с Kaiten.
    
    Порядок действий для каждого элемента:
    1. Ищем по ID, если есть - проверяем настройки в Kaiten
    2. Если настройки не совпадают - обновляем
    3. Если нет по ID - ищем по имени/title
    4. Если есть по имени - обновляем ID в settings.json и проверяем данные
    5. Если нет - создаём новый элемент и сохраняем ID
    
    Returns:
        Dict с результатами синхронизации
    """
    settings = open_settings()
    results = {
        'properties': {'created': [], 'updated': [], 'errors': []},
        'space': {'status': None, 'error': None},
        'boards': {'created': [], 'updated': [], 'errors': []},
        'columns': {'created': [], 'updated': [], 'errors': []},
        'card_types': {'created': [], 'updated': [], 'errors': []}
    }
    
    try:
        # Синхронизация пространства
        await sync_space(settings, results)
        
        # Синхронизация досок (если пространство синхронизировано успешно)
        if results['space']['status'] in ['ok', 'found', 'created'] and not results['space']['error']:
            await sync_boards(settings, results)
        
        # Синхронизация свойств
        await sync_properties(settings, results)
        
        # Синхронизация типов карточек
        await sync_card_types(settings, results)
        
        # Сохраняем обновленные настройки
        save_settings(settings)
        
    except Exception as e:
        logger.error(f"Ошибка при синхронизации настроек: {e}")
        results['error'] = str(e)
    
    async with kaiten as k:
        print('USERS')
        vr = await k.get_company_users(only_virtual=True)
        pprint(vr)

    return results


async def sync_space(settings: Dict[str, Any], results: Dict[str, Any]):
    """Синхронизирует пространство с Kaiten."""
    space_config = settings.get('space', {})
    space_id = space_config.get('id', 0)
    space_title = space_config.get('title', '')
    
    try:
        if space_id:
            # Проверяем существование по ID
            try:
                space = await kaiten.get_space(space_id)
                
                # Проверяем, совпадает ли название
                if space.title != space_title:
                    logger.info(f"Обновление пространства {space_id}: '{space.title}' -> '{space_title}'")
                    await kaiten.update_space(space_id, title=space_title)
                
                results['space']['status'] = 'ok'
                logger.info(f"Пространство {space_id} синхронизировано")
                
            except Exception as e:
                logger.warning(f"Пространство с ID {space_id} не найдено (будем искать по названию): {e}")
                space_id = 0
        
        if not space_id:
            # Ищем по названию
            spaces = await kaiten.get_spaces()
            found_space = None
            
            for space in spaces:
                if space.title == space_title:
                    found_space = space
                    break
            
            if found_space:
                # Обновляем ID в настройках
                space_config['id'] = found_space.id
                results['space']['status'] = 'found'
                logger.info(f"Найдено пространство '{space_title}' с ID {found_space.id}")
            else:
                # Создаём новое пространство
                new_space = await kaiten.create_space(
                    name=space_title,
                    description=space_config.get('description')
                )
                logger.info(f"API ответ создания пространства: {new_space._data}")
                space_config['id'] = new_space.id
                results['space']['status'] = 'created'
                logger.info(f"Создано новое пространство '{space_title}' с ID {new_space.id}")
                await asyncio.sleep(0.5)  # Небольшая задержка после создания
                
    except Exception as e:
        logger.error(f"Ошибка при синхронизации пространства: {e}")
        results['space']['error'] = str(e)


async def sync_boards(settings: Dict[str, Any], results: Dict[str, Any]):
    """Синхронизирует доски с Kaiten."""
    space_config = settings.get('space', {})
    space_id = space_config.get('id')
    boards_config = space_config.get('boards', {})
    
    if not space_id:
        logger.error("Не указан ID пространства для синхронизации досок")
        return
    
    try:
        # Получаем существующие доски
        existing_boards = await kaiten.get_boards(space_id)
        existing_boards_map = {board.title: board for board in existing_boards}
        existing_boards_id_map = {board.id: board for board in existing_boards}
        
        for board_key, board_config in boards_config.items():
            board_id = board_config.get('id', 0)
            board_title = board_config.get('title', '')
            
            try:
                if board_id and board_id in existing_boards_id_map:
                    # Доска найдена по ID
                    board = existing_boards_id_map[board_id]
                    
                    # Проверяем название
                    if board.title != board_title and isinstance(board_id, int):
                        logger.info(f"Обновление доски {board_id}: '{board.title}' -> '{board_title}'")
                        await kaiten.update_board(space_id, board_id, title=board_title)
                        results['boards']['updated'].append(board_key)
                    
                    # Синхронизируем колонки существующей доски
                    await sync_columns(board_config, space_id, results)
                    
                elif board_title in existing_boards_map:
                    # Нашли по названию - обновляем ID
                    board = existing_boards_map[board_title]
                    board_config['id'] = board.id
                    logger.info(f"Найдена доска '{board_title}' с ID {board.id}")
                    results['boards']['updated'].append(board_key)
                    
                    # Синхронизируем колонки найденной доски
                    await sync_columns(board_config, space_id, results)
                    
                else:
                    # Создаём новую доску с пустым массивом колонок
                    new_board = await kaiten.create_board(
                        title=board_title,
                        space_id=space_id,
                        description=board_config.get('description'),
                        columns=[]
                    )
                    logger.info(f"API ответ создания доски: {new_board._data}")
                    board_config['id'] = new_board.id
                    logger.info(f"Создана новая доска '{board_title}' с ID {new_board.id}")
                    results['boards']['created'].append(board_key)
                    await asyncio.sleep(0.5)  # Небольшая задержка после создания доски
                    
                    # После создания доски создаём колонки
                    if new_board.id is not None:
                        for idx, col_config in enumerate(board_config.get('columns', [])):
                            try:
                                new_column = await kaiten.create_column(
                                    title=col_config.get('title', ''),
                                    board_id=new_board.id,
                                    position=idx
                                )
                                logger.info(f"API ответ создания колонки: {new_column._data}")
                                col_config['id'] = new_column.id
                                logger.info(f"Создана колонка '{col_config.get('title')}' с ID {new_column.id}")
                                results['columns']['created'].append(f"{board_title}/{col_config.get('title')}")
                                await asyncio.sleep(0.3)  # Небольшая задержка между колонками
                            except Exception as e:
                                logger.error(f"Ошибка при создании колонки '{col_config.get('title')}': {e}")
                                results['columns']['errors'].append({
                                    'column': f"{board_title}/{col_config.get('title')}",
                                    'error': str(e)
                                })
                
            except Exception as e:
                logger.error(f"Ошибка при синхронизации доски '{board_key}': {e}")
                results['boards']['errors'].append({'board': board_key, 'error': str(e)})
                
    except Exception as e:
        logger.error(f"Ошибка при получении досок: {e}")


async def sync_columns(board_config: Dict[str, Any], space_id: int, results: Dict[str, Any]):
    """Синхронизирует колонки доски с Kaiten."""
    board_id = board_config.get('id')
    columns_config = board_config.get('columns', [])
    
    if not board_id:
        logger.warning("Не указан ID доски для синхронизации колонок")
        return
    
    try:
        # Получаем существующие колонки
        existing_columns = await kaiten.get_columns(board_id)
        existing_columns_map = {col.title: col for col in existing_columns}
        existing_columns_id_map = {col.id: col for col in existing_columns}
        
        for idx, column_config in enumerate(columns_config):
            column_id = column_config.get('id', 0)
            column_title = column_config.get('title', '')
            column_type = column_config.get('type', 1)
            
            try:
                if column_id and column_id in existing_columns_id_map:
                    # Колонка найдена по ID
                    column = existing_columns_id_map[column_id]
                    
                    # Проверяем название
                    if column.title != column_title and isinstance(board_id, int) and isinstance(column_id, int):
                        logger.info(f"Обновление колонки {column_id}: '{column.title}' -> '{column_title}'")
                        await kaiten.update_column(board_id, column_id, title=column_title)
                        results['columns']['updated'].append(f"{board_config.get('title')}/{column_title}")
                    
                elif column_title in existing_columns_map:
                    # Нашли по названию - обновляем ID
                    column = existing_columns_map[column_title]
                    column_config['id'] = column.id
                    logger.info(f"Найдена колонка '{column_title}' с ID {column.id}")
                    results['columns']['updated'].append(f"{board_config.get('title')}/{column_title}")
                    
                else:
                    # Создаём новую колонку
                    new_column = await kaiten.create_column(
                        title=column_title,
                        board_id=board_id,
                        position=idx
                    )
                    logger.info(f"API ответ создания колонки (sync): {new_column._data}")
                    column_config['id'] = new_column.id
                    logger.info(f"Создана новая колонка '{column_title}' с ID {new_column.id}")
                    results['columns']['created'].append(f"{board_config.get('title')}/{column_title}")
                    await asyncio.sleep(0.3)  # Небольшая задержка после создания колонки
                    
            except Exception as e:
                logger.error(f"Ошибка при синхронизации колонки '{column_title}': {e}")
                results['columns']['errors'].append({
                    'column': f"{board_config.get('title')}/{column_title}",
                    'error': str(e)
                })
                
    except Exception as e:
        logger.error(f"Ошибка при получении колонок доски {board_id}: {e}")


async def sync_properties(settings: Dict[str, Any], results: Dict[str, Any]):
    """Синхронизирует пользовательские свойства с Kaiten."""
    properties_config = settings.get('properties', {})
    
    try:
        # Получаем все существующие свойства из Kaiten
        existing_properties = await kaiten.get_custom_properties()
        existing_properties_map = {prop.name: prop for prop in existing_properties}
        existing_properties_id_map = {prop.id: prop for prop in existing_properties}
        
        for prop_key, prop_config in properties_config.items():
            prop_id = prop_config.get('id', 0)
            prop_name = prop_config.get('name', '')
            prop_type = prop_config.get('type', 'string')
            
            try:
                # Проверяем существование свойства по ID
                if prop_id and prop_id in existing_properties_id_map:
                    # Свойство найдено по ID
                    prop = existing_properties_id_map[prop_id]
                    logger.info(f"Найдено свойство '{prop_name}' с ID {prop_id}")
                    
                    # Синхронизация значений для select свойств
                    if prop_type == 'select' and isinstance(prop_id, int):
                        await sync_property_values(prop_id, prop_config, results)
                        
                elif prop_name in existing_properties_map:
                    # Нашли по названию - обновляем ID
                    prop = existing_properties_map[prop_name]
                    prop_config['id'] = prop.id
                    logger.info(f"Найдено свойство '{prop_name}' с ID {prop.id}")
                    
                    # Синхронизация значений для select свойств
                    if prop_type == 'select' and prop.id is not None:
                        await sync_property_values(prop.id, prop_config, results)
                else:
                    # Свойство не найдено - создаём новое
                    logger.info(f"Свойство '{prop_name}' ({prop_key}) не найдено в Kaiten, создаём новое")
                    
                    # Подготовка параметров для создания свойства
                    create_params = {
                        'name': prop_name,
                        'property_type': prop_type,
                        'show_on_facade': prop_config.get('show_on_facade', False),
                        'multiline': prop_config.get('multiline', False)
                    }
                    
                    # Дополнительные параметры для select
                    if prop_type == 'select':
                        create_params['multi_select'] = prop_config.get('multi_select', False)
                        create_params['colorful'] = prop_config.get('colorful', False)
                        if 'values_creatable_by_users' in prop_config:
                            create_params['values_creatable_by_users'] = prop_config.get('values_creatable_by_users', False)
                    
                    # Дополнительные данные
                    if 'data' in prop_config:
                        create_params['data'] = prop_config['data']
                    
                    # Создаём свойство
                    new_prop = await kaiten.create_custom_property(**create_params)
                    logger.info(f"API ответ создания свойства: {new_prop._data}")
                    prop_config['id'] = new_prop.id
                    logger.info(f"Создано новое свойство '{prop_name}' с ID {new_prop.id}")
                    await asyncio.sleep(0.5)  # Небольшая задержка после создания свойства
                    
                    # Синхронизация значений для select свойств
                    if prop_type == 'select' and new_prop.id is not None:
                        await sync_property_values(new_prop.id, prop_config, results)
                    
            except Exception as e:
                logger.error(f"Ошибка при синхронизации свойства '{prop_key}': {e}")
                results['properties']['errors'].append({
                    'property': prop_key,
                    'error': str(e)
                })
                
    except Exception as e:
        logger.error(f"Ошибка при синхронизации свойств: {e}")


async def sync_card_types(settings: Dict[str, Any], results: Dict[str, Any]):
    """Синхронизирует типы карточек с Kaiten."""
    card_types_config = settings.get('card_types', {})
    
    if not card_types_config:
        logger.info("Нет типов карточек для синхронизации")
        return
    
    try:
        # Получаем все существующие типы карточек из Kaiten
        existing_types = await kaiten.get_card_types()
        existing_types_map = {t['name']: t for t in existing_types}
        existing_types_id_map = {t['id']: t for t in existing_types}
        
        for type_key, type_config in card_types_config.items():
            type_id = type_config.get('id', 0)
            type_name = type_config.get('name', '')
            type_letter = type_config.get('letter', '')
            type_color = type_config.get('color', 2)  # По умолчанию цвет 2
            
            try:
                if type_id and type_id in existing_types_id_map:
                    # Тип найден по ID
                    existing_type = existing_types_id_map[type_id]
                    logger.info(f"Найден тип карточки '{type_name}' с ID {type_id}")
                    
                    # Проверяем, нужно ли обновить данные
                    needs_update = False
                    update_fields = {}
                    
                    if existing_type.get('name') != type_name and type_name:
                        update_fields['name'] = type_name
                        needs_update = True
                        
                    if existing_type.get('letter') != type_letter and type_letter:
                        update_fields['letter'] = type_letter
                        needs_update = True
                    
                    if needs_update:
                        logger.info(f"Обновление типа карточки {type_id}: {update_fields}")
                        await kaiten.update_card_type(type_id, **update_fields)
                        results['card_types']['updated'].append(type_key)
                    
                    # Обновляем конфиг из Kaiten если данные не указаны
                    if not type_name:
                        type_config['name'] = existing_type.get('name', '')
                    if not type_letter:
                        type_config['letter'] = existing_type.get('letter', '')
                    if 'color' not in type_config:
                        type_config['color'] = existing_type.get('color', 2)
                        
                elif type_name in existing_types_map:
                    # Нашли по названию - обновляем ID в настройках
                    existing_type = existing_types_map[type_name]
                    type_config['id'] = existing_type['id']
                    logger.info(f"Найден тип карточки '{type_name}' с ID {existing_type['id']}")
                    results['card_types']['updated'].append(type_key)
                    
                    # Проверяем, нужно ли обновить letter
                    if existing_type.get('letter') != type_letter and type_letter:
                        logger.info(f"Обновление letter типа карточки {existing_type['id']}: '{existing_type.get('letter')}' -> '{type_letter}'")
                        await kaiten.update_card_type(existing_type['id'], letter=type_letter)
                    
                    # Обновляем данные из Kaiten
                    if not type_letter:
                        type_config['letter'] = existing_type.get('letter', '')
                    if 'color' not in type_config:
                        type_config['color'] = existing_type.get('color', 2)
                        
                else:
                    # Тип не найден - создаём новый
                    if not type_name or not type_letter:
                        logger.warning(f"Пропускаем создание типа '{type_key}': отсутствует name или letter")
                        continue
                        
                    logger.info(f"Тип карточки '{type_name}' ({type_key}) не найден в Kaiten, создаём новый")
                    
                    new_type = await kaiten.create_card_type(
                        letter=type_letter,
                        name=type_name,
                        color=type_color
                    )
                    logger.info(f"API ответ создания типа карточки: {new_type}")
                    type_config['id'] = new_type['id']
                    type_config['color'] = new_type.get('color', type_color)
                    logger.info(f"Создан новый тип карточки '{type_name}' с ID {new_type['id']}")
                    results['card_types']['created'].append(type_key)
                    await asyncio.sleep(0.5)  # Небольшая задержка после создания
                    
            except Exception as e:
                logger.error(f"Ошибка при синхронизации типа карточки '{type_key}': {e}")
                results['card_types']['errors'].append({
                    'card_type': type_key,
                    'error': str(e)
                })
                
    except Exception as e:
        logger.error(f"Ошибка при синхронизации типов карточек: {e}")


async def sync_property_values(prop_id: int, prop_config: Dict[str, Any], results: Dict[str, Any]):
    """Синхронизирует значения select-свойства с Kaiten."""
    values_config = prop_config.get('values', {})
    
    if not values_config:
        return
    
    try:
        # Получаем существующие значения
        existing_values = await kaiten.get_property_select_values(prop_id)
        existing_values_map = {val['value']: val for val in existing_values}
        existing_values_map_lower = {val['value'].lower(): val for val in existing_values}
        existing_values_id_map = {val['id']: val for val in existing_values}
        
        for value_key, value_config in values_config.items():
            value_id = value_config.get('id', 0)
            value_name = value_config.get('name', '')
            
            try:
                if value_id and value_id in existing_values_id_map:
                    # Значение найдено по ID
                    value = existing_values_id_map[value_id]
                    
                    # Проверяем название (точное совпадение)
                    if value['value'] != value_name:
                        logger.info(f"Обновление значения {value_id}: '{value['value']}' -> '{value_name}'")
                        await kaiten.update_property_select_value(
                            prop_id,
                            value_id,
                            value=value_name
                        )
                        results['properties']['updated'].append(f"{prop_config.get('name')}/{value_name}")
                    
                elif value_name in existing_values_map:
                    # Нашли по точному названию - обновляем ID
                    value = existing_values_map[value_name]
                    value_config['id'] = value['id']
                    logger.info(f"Найдено значение '{value_name}' с ID {value['id']}")
                    results['properties']['updated'].append(f"{prop_config.get('name')}/{value_name}")
                    
                elif value_name.lower() in existing_values_map_lower:
                    # Нашли по названию без учёта регистра - обновляем название в Kaiten и ID в конфиге
                    value = existing_values_map_lower[value_name.lower()]
                    value_config['id'] = value['id']
                    logger.info(f"Найдено значение с другим регистром: '{value['value']}' -> '{value_name}' (ID {value['id']})")
                    
                    # Обновляем название в Kaiten на то, что в конфиге
                    await kaiten.update_property_select_value(
                        prop_id,
                        value['id'],
                        value=value_name
                    )
                    results['properties']['updated'].append(f"{prop_config.get('name')}/{value_name}")
                    
                else:
                    # Создаём новое значение
                    new_value = await kaiten.create_property_select_value(
                        prop_id,
                        value=value_name
                    )
                    logger.info(f"API ответ создания значения свойства: {new_value}")
                    value_config['id'] = new_value['id']
                    logger.info(f"Создано новое значение '{value_name}' с ID {new_value['id']}")
                    results['properties']['created'].append(f"{prop_config.get('name')}/{value_name}")
                    await asyncio.sleep(0.3)  # Небольшая задержка после создания значения
                    
            except Exception as e:
                logger.error(f"Ошибка при синхронизации значения '{value_name}': {e}")
                results['properties']['errors'].append({
                    'property_value': f"{prop_config.get('name')}/{value_name}",
                    'error': str(e)
                })
                
    except Exception as e:
        logger.error(f"Ошибка при синхронизации значений свойства {prop_id}: {e}")


def save_settings(settings: Dict[str, Any]):
    """Сохраняет обновлённые настройки в settings.json."""
    try:
        settings_path = '/json/settings.json'
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        logger.info("Настройки успешно сохранены")
    except Exception as e:
        logger.error(f"Ошибка при сохранении настроек: {e}")
        raise