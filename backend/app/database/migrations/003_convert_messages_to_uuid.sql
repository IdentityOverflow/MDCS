-- Migration: Convert messages table to use UUID primary keys
-- Date: 2025-01-21
-- Description: 
--   Update the messages table to use UUID primary keys instead of integer IDs
--   for consistency with conversations and better security

-- Step 1: Drop foreign key constraints that reference messages.id (if any)
-- (Currently no other tables reference messages, but we'll be safe)

-- Step 2: Add a new UUID column
ALTER TABLE messages ADD COLUMN new_id UUID DEFAULT gen_random_uuid();

-- Step 3: Update all rows to have UUID values
UPDATE messages SET new_id = gen_random_uuid() WHERE new_id IS NULL;

-- Step 4: Drop the old integer primary key constraint
ALTER TABLE messages DROP CONSTRAINT messages_pkey;

-- Step 5: Drop the old id column
ALTER TABLE messages DROP COLUMN id;

-- Step 6: Rename new_id to id
ALTER TABLE messages RENAME COLUMN new_id TO id;

-- Step 7: Set the new UUID column as primary key
ALTER TABLE messages ADD CONSTRAINT messages_pkey PRIMARY KEY (id);

-- Step 8: Add index for better performance
CREATE INDEX IF NOT EXISTS idx_messages_id ON messages(id);