-- Migration 008: Add first_message_id column to conversation_memories
-- This enables message ID-based compression logic to prevent duplicate compressions

-- Add the new column
ALTER TABLE conversation_memories 
ADD COLUMN first_message_id VARCHAR(100);

-- Add comment explaining the purpose
COMMENT ON COLUMN conversation_memories.first_message_id IS 'ID of the first message in the compressed range, used to prevent duplicate compressions of the same message set';