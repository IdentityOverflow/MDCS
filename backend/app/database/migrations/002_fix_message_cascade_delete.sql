-- Migration: Fix foreign key constraint for cascade delete
-- Date: 2025-01-21
-- Description: 
--   Update the messages.conversation_id foreign key constraint to include CASCADE DELETE
--   This ensures that when a conversation is deleted, all associated messages are also deleted

-- First, drop the existing foreign key constraint if it exists
-- (This might fail if the constraint doesn't exist, which is fine)
DO $$
BEGIN
    -- Try to drop the existing constraint
    BEGIN
        ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_conversation_id_fkey;
    EXCEPTION
        WHEN undefined_object THEN
            -- Constraint doesn't exist, continue
            NULL;
    END;
END $$;

-- Add the new foreign key constraint with CASCADE DELETE
ALTER TABLE messages 
ADD CONSTRAINT messages_conversation_id_fkey 
FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE;