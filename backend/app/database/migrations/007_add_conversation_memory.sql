-- Migration 007: Add conversation_memories table for long-term memory factory
-- Creates table to store AI-compressed conversation segment memories

-- Create the conversation_memories table
CREATE TABLE conversation_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    memory_sequence INTEGER NOT NULL,
    compressed_content TEXT NOT NULL,
    original_message_range VARCHAR(20) NOT NULL,
    message_count_at_compression INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create indexes for efficient querying
CREATE INDEX idx_conversation_memories_conversation_id ON conversation_memories(conversation_id);
CREATE INDEX idx_conversation_memories_sequence ON conversation_memories(conversation_id, memory_sequence);
CREATE INDEX idx_conversation_memories_created_at ON conversation_memories(created_at);

-- Add unique constraint to ensure one memory per conversation per sequence
ALTER TABLE conversation_memories 
ADD CONSTRAINT unique_conversation_memory_sequence 
UNIQUE (conversation_id, memory_sequence);

-- Add check constraint for message_count_at_compression
ALTER TABLE conversation_memories 
ADD CONSTRAINT check_positive_message_count 
CHECK (message_count_at_compression > 0);

-- Add check constraint for memory_sequence  
ALTER TABLE conversation_memories 
ADD CONSTRAINT check_positive_memory_sequence 
CHECK (memory_sequence > 0);

-- Add check constraint for non-empty compressed_content
ALTER TABLE conversation_memories 
ADD CONSTRAINT check_non_empty_content 
CHECK (char_length(compressed_content) > 0);

-- Comment the table and key columns
COMMENT ON TABLE conversation_memories IS 'Stores AI-compressed long-term conversation memories from fixed buffer window (messages 25-35)';
COMMENT ON COLUMN conversation_memories.conversation_id IS 'UUID of the conversation this memory belongs to';
COMMENT ON COLUMN conversation_memories.memory_sequence IS 'Sequential numbering of memories for this conversation (1, 2, 3...)';
COMMENT ON COLUMN conversation_memories.compressed_content IS 'AI-generated summary of the conversation segment';
COMMENT ON COLUMN conversation_memories.original_message_range IS 'Range of messages that were compressed (e.g., "25-35")';
COMMENT ON COLUMN conversation_memories.message_count_at_compression IS 'Total message count in conversation when this compression occurred';
COMMENT ON COLUMN conversation_memories.created_at IS 'Timestamp when this memory was created and stored';