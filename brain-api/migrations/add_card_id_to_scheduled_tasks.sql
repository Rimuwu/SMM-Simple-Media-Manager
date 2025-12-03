-- Миграция: Добавление поля card_id в таблицу scheduled_tasks
-- Дата: 2025-12-03
-- Описание: Добавляет поле card_id для связи запланированных задач с карточками

-- Добавляем колонку card_id если она еще не существует
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='scheduled_tasks' AND column_name='card_id'
    ) THEN
        ALTER TABLE scheduled_tasks 
        ADD COLUMN card_id UUID NULL;
        
        -- Создаем индекс для быстрого поиска задач по card_id
        CREATE INDEX idx_scheduled_tasks_card_id ON scheduled_tasks(card_id);
        
        RAISE NOTICE 'Колонка card_id успешно добавлена в таблицу scheduled_tasks';
    ELSE
        RAISE NOTICE 'Колонка card_id уже существует в таблице scheduled_tasks';
    END IF;
END $$;
