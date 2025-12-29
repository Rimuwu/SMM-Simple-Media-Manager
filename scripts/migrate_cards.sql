-- Migration: Refactor Card model - split JSON columns into separate tables
-- Migrate data from old flat structure to new relational structure
-- Run inside postgres container (see run_migration.py)

BEGIN;

-- ============ PHASE 1: Create new tables ============

-- 1. Create card_contents table
CREATE TABLE IF NOT EXISTS card_contents (
    id UUID PRIMARY KEY,
    card_id UUID NOT NULL REFERENCES cards(card_id) ON DELETE CASCADE,
    client_key VARCHAR(255),
    text TEXT,
    meta JSON NOT NULL DEFAULT '{}'::json,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX (card_id)
);

-- 2. Create card_files table
CREATE TABLE IF NOT EXISTS card_files (
    id UUID PRIMARY KEY,
    card_id UUID NOT NULL REFERENCES cards(card_id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL UNIQUE,
    original_filename VARCHAR(255) NOT NULL,
    size BIGINT NOT NULL,
    data_info JSON NOT NULL DEFAULT '{}'::json,
    "order" INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX (card_id)
);

-- 3. Create card_messages table
CREATE TABLE IF NOT EXISTS card_messages (
    id UUID PRIMARY KEY,
    card_id UUID NOT NULL REFERENCES cards(card_id) ON DELETE CASCADE,
    message_type VARCHAR(255) NOT NULL,
    message_id BIGINT NOT NULL,
    data_info VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX (card_id)
);

-- 4. Create card_editor_notes table
CREATE TABLE IF NOT EXISTS card_editor_notes (
    id UUID PRIMARY KEY,
    card_id UUID NOT NULL REFERENCES cards(card_id) ON DELETE CASCADE,
    author TEXT,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX (card_id)
);

-- 5. Create client_settings table
CREATE TABLE IF NOT EXISTS client_settings (
    id UUID PRIMARY KEY,
    card_id UUID NOT NULL REFERENCES cards(card_id) ON DELETE CASCADE,
    client_key VARCHAR(255),
    data JSON NOT NULL DEFAULT '{}'::json,
    type VARCHAR(255),
    INDEX (card_id)
);

-- 6. Create entities table
CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY,
    card_id UUID NOT NULL REFERENCES cards(card_id) ON DELETE CASCADE,
    client_key VARCHAR(255),
    data JSON NOT NULL DEFAULT '{}'::json,
    type VARCHAR(255),
    INDEX (card_id)
);

-- ============ PHASE 2: Prepare cards table ============

-- Add new columns if they don't exist
ALTER TABLE cards ADD COLUMN IF NOT EXISTS editor_id UUID REFERENCES users(user_id) ON DELETE SET NULL;
ALTER TABLE cards ADD COLUMN IF NOT EXISTS calendar_id VARCHAR(255);

-- Rename old columns temporarily for data migration
ALTER TABLE cards RENAME COLUMN content TO content_old;
ALTER TABLE cards RENAME COLUMN editor_notes TO editor_notes_old;
ALTER TABLE cards RENAME COLUMN clients_settings TO clients_settings_old;
ALTER TABLE cards RENAME COLUMN entities TO entities_old;
ALTER TABLE cards RENAME COLUMN complete_message_id TO complete_message_id_old;

-- ============ PHASE 3: Update scheduled_tasks table ============

-- Add created_at, updated_at if missing
ALTER TABLE scheduled_tasks ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE scheduled_tasks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- Add ForeignKey constraint if missing (the column should already exist)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'scheduled_tasks_card_id_fkey') THEN
    ALTER TABLE scheduled_tasks ADD CONSTRAINT scheduled_tasks_card_id_fkey 
      FOREIGN KEY (card_id) REFERENCES cards(card_id) ON DELETE CASCADE;
  END IF;
END$$;

-- ============ PHASE 4: Update users table ============

-- Add can_pick column if missing
ALTER TABLE users ADD COLUMN IF NOT EXISTS can_pick BOOLEAN NOT NULL DEFAULT FALSE;

-- ============ PHASE 5: Migrate data from old structure to new tables ============

-- 5.1 Migrate content to card_contents
-- Old format was: {"all": "content_text"} or similar
-- We'll put all content into default "all" client_key
DO $$
DECLARE
    card_rec RECORD;
    content_text TEXT;
    client_keys TEXT[];
BEGIN
    FOR card_rec IN SELECT card_id, content_old FROM cards WHERE content_old IS NOT NULL LOOP
        -- If content_old is a JSON object with "all" key
        IF card_rec.content_old ? 'all' THEN
            content_text := card_rec.content_old->>'all';
            INSERT INTO card_contents (id, card_id, client_key, text, meta)
            VALUES (gen_random_uuid(), card_rec.card_id, 'all', content_text, '{}'::json)
            ON CONFLICT DO NOTHING;
        END IF;
    END LOOP;
END$$;

-- 5.2 Migrate editor_notes (was list of dicts) to card_editor_notes
DO $$
DECLARE
    card_rec RECORD;
    note JSON;
BEGIN
    FOR card_rec IN SELECT card_id, editor_notes_old FROM cards WHERE editor_notes_old IS NOT NULL AND editor_notes_old::text != '[]' LOOP
        -- editor_notes_old is a JSON array
        FOR note IN SELECT json_array_elements(card_rec.editor_notes_old) LOOP
            INSERT INTO card_editor_notes (id, card_id, author, content)
            VALUES (
                gen_random_uuid(),
                card_rec.card_id,
                note->>'author',
                note->>'content'
            )
            ON CONFLICT DO NOTHING;
        END LOOP;
    END LOOP;
END$$;

-- 5.3 Migrate complete_message_id to card_messages
-- Format was: {"client_key": {"post_id": int, "info_id": int}, ...}
DO $$
DECLARE
    card_rec RECORD;
    client_key TEXT;
    msg_data JSON;
BEGIN
    FOR card_rec IN SELECT card_id, complete_message_id_old FROM cards 
                    WHERE complete_message_id_old IS NOT NULL AND complete_message_id_old::text != '{}' LOOP
        FOR client_key, msg_data IN 
            SELECT key, value FROM json_each(card_rec.complete_message_id_old)
        LOOP
            INSERT INTO card_messages (id, card_id, message_type, message_id, data_info)
            VALUES (
                gen_random_uuid(),
                card_rec.card_id,
                'complete_preview',
                COALESCE((msg_data->>'post_id')::BIGINT, 0),
                client_key
            )
            ON CONFLICT DO NOTHING;
        END LOOP;
    END LOOP;
END$$;

-- 5.4 Migrate forum_message_id to card_messages
DO $$
DECLARE
    card_rec RECORD;
BEGIN
    FOR card_rec IN SELECT card_id, forum_message_id FROM cards 
                    WHERE forum_message_id IS NOT NULL LOOP
        INSERT INTO card_messages (id, card_id, message_type, message_id)
        VALUES (gen_random_uuid(), card_rec.card_id, 'forum', card_rec.forum_message_id)
        ON CONFLICT DO NOTHING;
    END LOOP;
END$$;

-- 5.5 Migrate clients_settings (JSON object) to client_settings table
DO $$
DECLARE
    card_rec RECORD;
    client_key TEXT;
    settings JSON;
BEGIN
    FOR card_rec IN SELECT card_id, clients_settings_old FROM cards 
                    WHERE clients_settings_old IS NOT NULL AND clients_settings_old::text != '{}' LOOP
        FOR client_key, settings IN 
            SELECT key, value FROM json_each(card_rec.clients_settings_old)
        LOOP
            INSERT INTO client_settings (id, card_id, client_key, data)
            VALUES (gen_random_uuid(), card_rec.card_id, client_key, settings)
            ON CONFLICT DO NOTHING;
        END LOOP;
    END LOOP;
END$$;

-- 5.6 Migrate entities (JSON object) to entities table
DO $$
DECLARE
    card_rec RECORD;
    client_key TEXT;
    entity_data JSON;
BEGIN
    FOR card_rec IN SELECT card_id, entities_old FROM cards 
                    WHERE entities_old IS NOT NULL AND entities_old::text != '{}' LOOP
        FOR client_key, entity_data IN 
            SELECT key, value FROM json_each(card_rec.entities_old)
        LOOP
            INSERT INTO entities (id, card_id, client_key, data)
            VALUES (gen_random_uuid(), card_rec.card_id, client_key, entity_data)
            ON CONFLICT DO NOTHING;
        END LOOP;
    END LOOP;
END$$;

-- ============ PHASE 6: Drop old columns from cards table ============

ALTER TABLE cards DROP COLUMN IF EXISTS content_old;
ALTER TABLE cards DROP COLUMN IF EXISTS editor_notes_old;
ALTER TABLE cards DROP COLUMN IF EXISTS clients_settings_old;
ALTER TABLE cards DROP COLUMN IF EXISTS entities_old;
ALTER TABLE cards DROP COLUMN IF EXISTS complete_message_id_old;
ALTER TABLE cards DROP COLUMN IF EXISTS forum_message_id;

-- ============ PHASE 7: Verify migration ============

-- Check that no critical data was lost
DO $$
BEGIN
    IF (SELECT COUNT(*) FROM cards) > 0 AND (SELECT COUNT(*) FROM card_contents) = 0 THEN
        RAISE WARNING 'No content was migrated to card_contents. Check your data.';
    END IF;
END$$;

COMMIT;

-- End of migration
