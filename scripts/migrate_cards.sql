-- Migration: convert content -> {"all": content}, add editor_id, clients_settings, entities
-- Uses JSON (not JSONB). Run inside postgres container (see run_migration.py)

BEGIN;

-- 1) добавить колонки, если их нет
ALTER TABLE cards ADD COLUMN IF NOT EXISTS editor_id UUID;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'cards_editor_id_fkey') THEN
    ALTER TABLE cards ADD CONSTRAINT cards_editor_id_fkey FOREIGN KEY (editor_id) REFERENCES users(user_id) ON DELETE SET NULL;
  END IF;
END$$;

ALTER TABLE cards ADD COLUMN IF NOT EXISTS clients_settings JSON;
ALTER TABLE cards ADD COLUMN IF NOT EXISTS entities JSON;
ALTER TABLE cards ADD COLUMN IF NOT EXISTS content_new JSON;

-- 2) подготовить значения
UPDATE cards SET editor_id = NULL;
UPDATE cards SET clients_settings = '{}'::json WHERE clients_settings IS NULL;
UPDATE cards SET entities = '{}'::json WHERE entities IS NULL;
UPDATE cards SET complete_message_id = '{}'::json WHERE complete_message_id IS NULL;

-- 3) заполнить content_new как {"all": <старое content>}
UPDATE cards
SET content_new = json_build_object('all', content);

-- безопасность: если что-то пошло не так, остановим миграцию
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM cards WHERE content_new IS NULL) THEN
    RAISE EXCEPTION 'Migration aborted: content_new contains NULL values';
  END IF;
END$$;

-- 4) заменить старую колонку content на новую и установить ограничения/значения по умолчанию
ALTER TABLE cards DROP COLUMN IF EXISTS content;
ALTER TABLE cards RENAME COLUMN content_new TO content;
ALTER TABLE cards ALTER COLUMN content SET DEFAULT '{}'::json;
ALTER TABLE cards ALTER COLUMN content SET NOT NULL;

-- привести complete_message_id к json и сделать NOT NULL + DEFAULT
ALTER TABLE cards ALTER COLUMN complete_message_id TYPE JSON USING complete_message_id::json;
ALTER TABLE cards ALTER COLUMN complete_message_id SET DEFAULT '{}'::json;
ALTER TABLE cards ALTER COLUMN complete_message_id SET NOT NULL;

-- установить DEFAULT и NOT NULL для clients_settings и entities
ALTER TABLE cards ALTER COLUMN clients_settings SET DEFAULT '{}'::json;
ALTER TABLE cards ALTER COLUMN clients_settings SET NOT NULL;
ALTER TABLE cards ALTER COLUMN entities SET DEFAULT '{}'::json;
ALTER TABLE cards ALTER COLUMN entities SET NOT NULL;

COMMIT;

-- End of migration
