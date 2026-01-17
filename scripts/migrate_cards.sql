-- Migration: Add 'hide' column to card_files table
-- Run inside postgres container (see run_migration.py)

BEGIN;

-- Add 'hide' column to card_files if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='card_files' AND column_name='hide') THEN
        ALTER TABLE card_files ADD COLUMN hide BOOLEAN NOT NULL DEFAULT FALSE;
        RAISE NOTICE 'Added hide column to card_files table';
    ELSE
        RAISE NOTICE 'Column hide already exists in card_files table';
    END IF;
END$$;

-- Ensure all existing records have hide=false (in case column existed but had NULL values)
UPDATE card_files SET hide = FALSE WHERE hide IS NULL;

-- Verify migration
DO $$
BEGIN
    RAISE NOTICE 'Migration verification:';
    RAISE NOTICE 'Card files total: %', (SELECT COUNT(*) FROM card_files);
    RAISE NOTICE 'Card files with hide=false: %', (SELECT COUNT(*) FROM card_files WHERE hide = FALSE);
    RAISE NOTICE 'Card files with hide=true: %', (SELECT COUNT(*) FROM card_files WHERE hide = TRUE);
END$$;

COMMIT;

-- End of migration
