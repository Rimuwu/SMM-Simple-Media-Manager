
import asyncio
import os
from kaiten_client import KaitenClient
from kaiten_client.models.checklist_item import ChecklistItem
from pprint import pprint
from dotenv import load_dotenv

load_dotenv()

KAITEN_DOMAIN=os.getenv("KAITEN_DOMAIN")
KAITEN_TOKEN=os.getenv("KAITEN_TOKEN")

async def main():
    """Демонстрация основных возможностей клиента."""
    print("🚀 Запуск демонстрации Kaiten API клиента")

    async with KaitenClient(KAITEN_TOKEN, KAITEN_DOMAIN) as client:
        
        # Получаем первую область (пространство)
        print("\n📁 Получение пространств...")
        spaces = await client.get_spaces()
        if not spaces:
            print("❌ Нет доступных пространств")
            return
        
        space = spaces[0]
        print(f"✅ Используем пространство: {space.title} (ID: {space.id})")
        
        # Получаем первую доску в пространстве
        print("\n📋 Получение досок...")
        boards = await space.get_boards()
        if not boards:
            print("❌ Нет досок в пространстве")
            return
        
        board = boards[0]
        print(f"✅ Используем доску: {board.title} (ID: {board.id})")
        
        # Получаем первую колонку доски
        print("\n📝 Получение колонок...")
        columns = await board.get_columns()
        if not columns:
            print("❌ Нет колонок в доске")
            return
        
        column = columns[0]
        print(f"✅ Используем колонку: {column.title} (ID: {column.id})")
        
        # Создаем карточку
        print("\n🎯 Создание карточки...")
        card = await client.create_card(
            board_id=board.id,
            title="Карточка с чек-листом",
            column_id=column.id,
            description="Тестовая карточка для демонстрации работы с чек-листами"
        )
        print(f"✅ Карточка создана: {card.title} (ID: {card.id})")
        
        # Создаем чек-лист для карточки
        print("\n✅ Создание чек-листа...")
        checklist = await card.create_checklist(
            name="План выполнения задачи",
            sort_order=1.0
        )
        print(f"✅ Чек-лист создан: {checklist.name} (ID: {checklist.id})")
        
        # Добавляем элементы в чек-лист
        print("\n📋 Добавление элементов в чек-лист...")
        
        items_to_add = [
            {"text": "Анализ требований", "sort_order": 1.0},
            {"text": "Создание технического задания", "sort_order": 2.0},
            {"text": "Разработка", "sort_order": 3.0, "due_date": "2025-09-10"},
            {"text": "Тестирование", "sort_order": 4.0},
            {"text": "Развертывание", "sort_order": 5.0, "checked": False},
            {"text": "Развертывание", "sort_order": 6.0, "checked": True},
            {"text": "Развертывание", "sort_order": 7.0, "checked": False}
        ]
        
        created_items = []
        for item_data in items_to_add:
            item = await checklist.add_item(**item_data)
            created_items.append(item)
            print(f"  ✓ Добавлен элемент: {item.text}")
        
        # Отмечаем первый элемент как выполненный
        print("\n✔️ Отмечаем первый элемент как выполненный...")
        first_item: ChecklistItem = created_items[0]
        await first_item.toggle_checked()
        print(f"  ✅ Элемент '{first_item.text}' отмечен как выполненный")
        
        # Показываем статистику чек-листа
        print("\n📊 Статистика чек-листа...")
        await checklist.refresh()  # Обновляем данные чек-листа
        stats = checklist.get_completion_stats()
        print(f"  📈 Прогресс: {stats['completed']}/{stats['total']} ({stats['percentage']}%)")
        print(f"  🎯 Завершен: {'Да' if checklist.is_completed() else 'Нет'}")
        
        # Получаем все чек-листы карточки
        print("\n📝 Получение всех чек-листов карточки...")
        all_checklists = await card.get_checklists()
        print(f"  🔍 Найдено чек-листов: {len(all_checklists)}")
        
        if all_checklists:
            for cl in all_checklists:
                stats = cl.get_completion_stats()
                print(f"  📋 {cl.name}: {stats['completed']}/{stats['total']} элементов")
        else:
            print("  ℹ️ Чек-листы не найдены или не загружены")
            print("  🔄 Попробуем обновить данные карточки...")
            # Принудительно обновляем карточку с чек-листами
            updated_card = await client.get_card(card.id, additional_fields='checklists')
            if hasattr(updated_card, '_data') and 'checklists' in updated_card._data:
                print(f"  📊 В данных карточки найдено: {len(updated_card._data.get('checklists', []))} чек-листов")
        
        # Демонстрация работы с элементами чек-листа
        print("\n🔧 Демонстрация управления элементами...")
        
        # Обновляем текст второго элемента
        second_item = created_items[1]
        await second_item.update(text="Создание подробного технического задания")
        print(f"  ✏️ Обновлен текст элемента: {second_item.text}")
        
        # Устанавливаем срок для третьего элемента
        third_item = created_items[4]
        await third_item.set_due_date("2025-09-25")
        print(f"  📅 Установлен срок для элемента '{third_item.text}': {third_item.due_date}")
        
        # Проверяем просроченные элементы
        overdue_items = checklist.get_overdue_items()
        if overdue_items:
            print(f"\n⚠️ Найдено просроченных элементов: {len(overdue_items)}")
            for item in overdue_items:
                print(f"  ⏰ {item['text']} (срок: {item['due_date']})")
        else:
            print("\n✅ Просроченных элементов нет")
        
        print(f"\n🎉 Демонстрация завершена! Карточка ID: {card.id}, Чек-лист ID: {checklist.id}")
        print("📋 Создана карточка с полнофункциональным чек-листом")


if __name__ == "__main__":
    asyncio.run(main())