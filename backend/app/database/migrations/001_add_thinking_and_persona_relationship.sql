-- Migration: Add thinking field to messages and persona relationship to conversations
-- Date: 2025-01-21
-- Description: 
--   1. Add thinking TEXT field to messages table for AI reasoning content
--   2. Add persona_id foreign key to conversations table to associate conversations with personas

-- Add thinking field to messages table
ALTER TABLE messages ADD COLUMN thinking TEXT;

-- Add persona_id foreign key to conversations table
ALTER TABLE conversations ADD COLUMN persona_id UUID;

-- Add foreign key constraint for persona_id
ALTER TABLE conversations 
ADD CONSTRAINT fk_conversations_persona_id 
FOREIGN KEY (persona_id) REFERENCES personas(id) ON DELETE SET NULL;

-- Add index for better query performance
CREATE INDEX idx_conversations_persona_id ON conversations(persona_id);

-- Update the conversation repr in the model will be handled by SQLAlchemy automatically