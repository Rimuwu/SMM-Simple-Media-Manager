-- Migration: Refactor Card model - split JSON columns into separate tables
-- Safe migration that checks for existing columns and creates tables as needed
-- Run inside postgres container (see run_migration.py)

BEGIN;

-- ============ PHASE 1: Create new tables (idempotent) ============

-- 1. Create card_contents table
CREATE TABLE IF NOT EXISTS card_contents (
    id UUID PRIMARY KEY,
    card_id UUID NOT NULL REFERENCES cards(card_id) ON DELETE CASCADE,
    client_key VARCHAR(255),
    text TEXT,
    meta JSON NOT NULL DEFAULT '{}'::json,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_card_contents_card_id ON card_contents(card_id);

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
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_card_files_card_id ON card_files(card_id);

-- 3. Create card_messages table
CREATE TABLE IF NOT EXISTS card_messages (
    id UUID PRIMARY KEY,
    card_id UUID NOT NULL REFERENCES cards(card_id) ON DELETE CASCADE,
    message_type VARCHAR(255) NOT NULL,
    message_id BIGINT NOT NULL,
    data_info VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_card_messages_card_id ON card_messages(card_id);

-- 4. Create card_editor_notes table
CREATE TABLE IF NOT EXISTS card_editor_notes (
    id UUID PRIMARY KEY,
    card_id UUID NOT NULL REFERENCES cards(card_id) ON DELETE CASCADE,
    author TEXT,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_card_editor_notes_card_id ON card_editor_notes(card_id);

-- 5. Create client_settings table
CREATE TABLE IF NOT EXISTS client_settings (
    id UUID PRIMARY KEY,
    card_id UUID NOT NULL REFERENCES cards(card_id) ON DELETE CASCADE,
    client_key VARCHAR(255),
    data JSON NOT NULL DEFAULT '{}'::json,
    type VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_client_settings_card_id ON client_settings(card_id);

-- 6. Create entities table
CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY,
    card_id UUID NOT NULL REFERENCES cards(card_id) ON DELETE CASCADE,
    client_key VARCHAR(255),
    data JSON NOT NULL DEFAULT '{}'::json,
    type VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_entities_card_id ON entities(card_id);

-- ============ PHASE 2: Ensure cards table has required columns ============

-- Only add columns if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cards' AND column_name='editor_id') THEN
        ALTER TABLE cards ADD COLUMN editor_id UUID REFERENCES users(user_id) ON DELETE SET NULL;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cards' AND column_name='calendar_id') THEN
        ALTER TABLE cards ADD COLUMN calendar_id VARCHAR(255);
    END IF;
END$$;

-- ============ PHASE 3: Update scheduled_tasks table ============

-- Only add columns if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='scheduled_tasks' AND column_name='created_at') THEN
        ALTER TABLE scheduled_tasks ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='scheduled_tasks' AND column_name='updated_at') THEN
        ALTER TABLE scheduled_tasks ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
    END IF;
END$$;

-- Add ForeignKey constraint if missing
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'scheduled_tasks_card_id_fkey') THEN
    ALTER TABLE scheduled_tasks ADD CONSTRAINT scheduled_tasks_card_id_fkey 
      FOREIGN KEY (card_id) REFERENCES cards(card_id) ON DELETE CASCADE;
  END IF;
END$$;

-- ============ PHASE 4: Update users table ============

-- Only add column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='can_pick') THEN
        ALTER TABLE users ADD COLUMN can_pick BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END$$;

-- ============ PHASE 5: Data migration (only if old columns exist) ============

-- Migrate data ONLY if old content columns still exist
DO $$
DECLARE
    has_content_col BOOLEAN;
    has_editor_notes_col BOOLEAN;
    has_clients_settings_col BOOLEAN;
    has_entities_col BOOLEAN;
    has_complete_message_col BOOLEAN;
    has_forum_message_col BOOLEAN;
BEGIN
    -- Check if old columns exist
    has_content_col := EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cards' AND column_name='content');
    has_editor_notes_col := EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cards' AND column_name='editor_notes');
    has_clients_settings_col := EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cards' AND column_name='clients_settings');
    has_entities_col := EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cards' AND column_name='entities');
    has_complete_message_col := EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cards' AND column_name='complete_message_id');
    has_forum_message_col := EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cards' AND column_name='forum_message_id');
    
    -- Only proceed if we have old columns to migrate
    IF has_content_col OR has_editor_notes_col OR has_clients_settings_col OR has_entities_col OR has_complete_message_col OR has_forum_message_col THEN
        RAISE NOTICE 'Old columns found. Starting data migration...';
        
        -- Migrate content to card_contents
        IF has_content_col THEN
            INSERT INTO card_contents (id, card_id, client_key, text, meta)
            SELECT gen_random_uuid(), card_id, 'all', cards.content->>'all', '{}'::json
            FROM cards
            WHERE cards.content IS NOT NULL
            AND cards.content::text != '{}'
            ON CONFLICT DO NOTHING;
        END IF;
        
        -- Migrate editor_notes to card_editor_notes
        IF has_editor_notes_col THEN
            INSERT INTO card_editor_notes (id, card_id, author, content)
            SELECT gen_random_uuid(), c.card_id, note->>'author', note->>'content'
            FROM cards c, json_array_elements(c.editor_notes) AS note
            WHERE c.editor_notes IS NOT NULL
            AND c.editor_notes::text != '[]'
            ON CONFLICT DO NOTHING;
        END IF;
        
        -- Migrate clients_settings to client_settings
        IF has_clients_settings_col THEN
            INSERT INTO client_settings (id, card_id, client_key, data)
            SELECT gen_random_uuid(), c.card_id, key, value
            FROM cards c, json_each(c.clients_settings) AS t(key, value)
            WHERE c.clients_settings IS NOT NULL
            AND c.clients_settings::text != '{}'
            ON CONFLICT DO NOTHING;
        END IF;
        
        -- Migrate entities to entities table
        IF has_entities_col THEN
            INSERT INTO entities (id, card_id, client_key, data)
            SELECT gen_random_uuid(), c.card_id, key, value
            FROM cards c, json_each(c.entities) AS t(key, value)
            WHERE c.entities IS NOT NULL
            AND c.entities::text != '{}'
            ON CONFLICT DO NOTHING;
        END IF;
        
        -- Migrate complete_message_id to card_messages
        IF has_complete_message_col THEN
            INSERT INTO card_messages (id, card_id, message_type, message_id, data_info)
            SELECT gen_random_uuid(), c.card_id, 'complete_preview', 
                   COALESCE((value->>'post_id')::BIGINT, 0), key
            FROM cards c, json_each(c.complete_message_id) AS t(key, value)
            WHERE c.complete_message_id IS NOT NULL
            AND c.complete_message_id::text != '{}'
            ON CONFLICT DO NOTHING;
        END IF;
        
        -- Migrate forum_message_id to card_messages
        IF has_forum_message_col THEN
            INSERT INTO card_messages (id, card_id, message_type, message_id)
            SELECT gen_random_uuid(), card_id, 'forum', forum_message_id
            FROM cards
            WHERE forum_message_id IS NOT NULL
            ON CONFLICT DO NOTHING;
        END IF;
        
        RAISE NOTICE 'Data migration completed.';
    ELSE
        RAISE NOTICE 'No old columns found. Database is already in new format.';
    END IF;
END$$;

-- ============ PHASE 6: Drop old columns (only if they exist) ============

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cards' AND column_name='content') THEN
        ALTER TABLE cards DROP COLUMN content;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cards' AND column_name='editor_notes') THEN
        ALTER TABLE cards DROP COLUMN editor_notes;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cards' AND column_name='clients_settings') THEN
        ALTER TABLE cards DROP COLUMN clients_settings;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cards' AND column_name='entities') THEN
        ALTER TABLE cards DROP COLUMN entities;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cards' AND column_name='complete_message_id') THEN
        ALTER TABLE cards DROP COLUMN complete_message_id;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cards' AND column_name='forum_message_id') THEN
        ALTER TABLE cards DROP COLUMN forum_message_id;
    END IF;
END$$;

-- ============ Verify migration ============

DO $$
BEGIN
    RAISE NOTICE 'Migration verification:';
    RAISE NOTICE 'Cards: %', (SELECT COUNT(*) FROM cards);
    RAISE NOTICE 'Card contents: %', (SELECT COUNT(*) FROM card_contents);
    RAISE NOTICE 'Card files: %', (SELECT COUNT(*) FROM card_files);
    RAISE NOTICE 'Card messages: %', (SELECT COUNT(*) FROM card_messages);
    RAISE NOTICE 'Card editor notes: %', (SELECT COUNT(*) FROM card_editor_notes);
    RAISE NOTICE 'Client settings: %', (SELECT COUNT(*) FROM client_settings);
    RAISE NOTICE 'Entities: %', (SELECT COUNT(*) FROM entities);
    RAISE NOTICE 'Scheduled tasks: %', (SELECT COUNT(*) FROM scheduled_tasks);
END$$;

COMMIT;

-- End of migration
