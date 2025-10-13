-- ============================================
-- Project 2501 Database Initialization Script
-- ============================================
-- Creates complete database schema in final state
-- Consolidates all migrations (001-008) into single schema
-- Designed for Docker deployment with automatic database setup
-- ============================================

\echo '=== Starting Project 2501 Database Initialization ==='

-- Enable UUID extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
\echo '✓ UUID extension enabled'

-- ============================================
-- Create Enums
-- ============================================

CREATE TYPE execution_context_enum AS ENUM ('IMMEDIATE', 'POST_RESPONSE', 'ON_DEMAND');
\echo '✓ Enum created: execution_context_enum'

-- ============================================
-- Create Tables
-- ============================================

-- Personas table
CREATE TABLE personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template TEXT NOT NULL,
    mode VARCHAR(20) NOT NULL DEFAULT 'reactive',
    loop_frequency VARCHAR(10),
    first_message TEXT,
    image_path VARCHAR(500),
    extra_data JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_persona_name UNIQUE (name),
    CONSTRAINT valid_persona_mode CHECK (mode IN ('reactive', 'autonomous')),
    CONSTRAINT valid_loop_frequency CHECK (
        loop_frequency IS NULL OR
        (mode = 'autonomous' AND loop_frequency ~ '^[0-9]*\.?[0-9]+$' AND CAST(loop_frequency AS FLOAT) > 0)
    )
);

COMMENT ON TABLE personas IS 'AI persona configurations with system prompt templates';
COMMENT ON CONSTRAINT unique_persona_name ON personas IS 'Prevents duplicate persona names for better user experience';
COMMENT ON CONSTRAINT valid_persona_mode ON personas IS 'Ensures only valid persona operating modes: reactive or autonomous';
COMMENT ON CONSTRAINT valid_loop_frequency ON personas IS 'Validates loop frequency is a positive float when persona is in autonomous mode';
\echo '✓ Table created: personas'

-- Modules table
CREATE TABLE modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT,
    type VARCHAR(20) NOT NULL DEFAULT 'simple',
    trigger_pattern VARCHAR(500),
    script TEXT,
    execution_context execution_context_enum NOT NULL DEFAULT 'ON_DEMAND',
    requires_ai_inference BOOLEAN NOT NULL DEFAULT FALSE,
    script_analysis_metadata JSONB DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_module_name UNIQUE (name),
    CONSTRAINT valid_module_name_format CHECK (
        name ~ '^[a-z][a-z0-9_]{0,49}$' AND
        LENGTH(name) <= 50
    )
);

COMMENT ON TABLE modules IS 'Cognitive system modules (simple text or advanced Python scripts)';
COMMENT ON CONSTRAINT unique_module_name ON modules IS 'Ensures module names are unique for @module_name template resolution';
COMMENT ON CONSTRAINT valid_module_name_format ON modules IS 'Enforces cognitive engine naming policy: start with letter, lowercase/numbers/underscores only, max 50 chars';
COMMENT ON COLUMN modules.content IS 'Module content - can be empty for modules that will be populated dynamically';
COMMENT ON COLUMN modules.execution_context IS 'When module executes: immediate (during template resolution), post_response (after AI response), on_demand (triggered)';
COMMENT ON COLUMN modules.requires_ai_inference IS 'Whether module script uses AI generation/reflection functions (auto-detected)';
COMMENT ON COLUMN modules.script_analysis_metadata IS 'Metadata about script analysis (detected functions, complexity, etc.)';
\echo '✓ Table created: modules'

-- Conversations table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    persona_id UUID REFERENCES personas(id) ON DELETE SET NULL,
    provider_type VARCHAR(50),
    provider_config JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE conversations IS 'Chat conversation sessions linked to personas';
\echo '✓ Table created: conversations'

-- Messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    thinking TEXT,
    extra_data JSONB,
    input_tokens INTEGER,
    output_tokens INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE messages IS 'Individual messages within conversations with optional thinking content';
COMMENT ON COLUMN messages.thinking IS 'AI reasoning content for native reasoning models';
\echo '✓ Table created: messages'

-- Conversation States table
CREATE TABLE conversation_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    module_id UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    execution_stage VARCHAR(20) NOT NULL CHECK (execution_stage IN ('stage4', 'stage5')),
    variables JSONB NOT NULL DEFAULT '{}',
    execution_metadata JSONB DEFAULT '{}',
    executed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(conversation_id, module_id, execution_stage)
);

COMMENT ON TABLE conversation_states IS 'Stores execution state for POST_RESPONSE modules across conversations';
COMMENT ON COLUMN conversation_states.execution_stage IS 'Stage 4 (non-AI) or Stage 5 (AI-powered) post-response execution';
COMMENT ON COLUMN conversation_states.variables IS 'Module script output variables stored as JSON for next conversation';
COMMENT ON COLUMN conversation_states.execution_metadata IS 'Metadata about script execution (success, timing, errors, etc.)';
\echo '✓ Table created: conversation_states'

-- Conversation Memories table
CREATE TABLE conversation_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    memory_sequence INTEGER NOT NULL CHECK (memory_sequence > 0),
    compressed_content TEXT NOT NULL CHECK (char_length(compressed_content) > 0),
    original_message_range VARCHAR(20) NOT NULL,
    message_count_at_compression INTEGER NOT NULL CHECK (message_count_at_compression > 0),
    first_message_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    UNIQUE (conversation_id, memory_sequence)
);

COMMENT ON TABLE conversation_memories IS 'Stores AI-compressed long-term conversation memories from fixed buffer window (messages 25-35)';
COMMENT ON COLUMN conversation_memories.conversation_id IS 'UUID of the conversation this memory belongs to';
COMMENT ON COLUMN conversation_memories.memory_sequence IS 'Sequential numbering of memories for this conversation (1, 2, 3...)';
COMMENT ON COLUMN conversation_memories.compressed_content IS 'AI-generated summary of the conversation segment';
COMMENT ON COLUMN conversation_memories.original_message_range IS 'Range of messages that were compressed (e.g., "25-35")';
COMMENT ON COLUMN conversation_memories.message_count_at_compression IS 'Total message count in conversation when this compression occurred';
COMMENT ON COLUMN conversation_memories.first_message_id IS 'ID of the first message in the compressed range, used to prevent duplicate compressions of the same message set';
COMMENT ON COLUMN conversation_memories.created_at IS 'Timestamp when this memory was created and stored';
\echo '✓ Table created: conversation_memories'

-- ============================================
-- Create Indexes
-- ============================================

\echo '=== Creating indexes for performance ==='

-- Personas indexes
CREATE INDEX idx_personas_name ON personas(name);
CREATE INDEX idx_personas_mode ON personas(mode);
CREATE INDEX idx_personas_active ON personas(is_active);

-- Modules indexes
CREATE INDEX idx_modules_name ON modules(name);
CREATE INDEX idx_modules_type ON modules(type);
CREATE INDEX idx_modules_active ON modules(is_active);
CREATE INDEX idx_modules_execution_context ON modules(execution_context);
CREATE INDEX idx_modules_ai_inference ON modules(requires_ai_inference);
CREATE INDEX idx_modules_context_ai_active ON modules(execution_context, requires_ai_inference, is_active);

-- Conversations indexes
CREATE INDEX idx_conversations_persona_id ON conversations(persona_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at);

-- Messages indexes
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- Conversation States indexes
CREATE INDEX idx_conversation_states_conversation_id ON conversation_states(conversation_id);
CREATE INDEX idx_conversation_states_module_id ON conversation_states(module_id);
CREATE INDEX idx_conversation_states_executed_at ON conversation_states(executed_at);

-- Conversation Memories indexes
CREATE INDEX idx_conversation_memories_conversation_id ON conversation_memories(conversation_id);
CREATE INDEX idx_conversation_memories_sequence ON conversation_memories(conversation_id, memory_sequence);
CREATE INDEX idx_conversation_memories_created_at ON conversation_memories(created_at);

\echo '✓ All indexes created'

-- ============================================
-- Create Triggers for updated_at
-- ============================================

\echo '=== Creating triggers for automatic updated_at ==='

-- Create function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add triggers to tables with updated_at column
CREATE TRIGGER update_personas_updated_at BEFORE UPDATE ON personas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_modules_updated_at BEFORE UPDATE ON modules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_messages_updated_at BEFORE UPDATE ON messages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

\echo '✓ Triggers created for automatic updated_at'

-- ============================================
-- Completion
-- ============================================

\echo '=== Project 2501 Database Initialization Complete ==='
\echo 'Database: project2501'
\echo 'Schema version: Equivalent to migrations 001-008'
\echo 'Tables: personas, modules, conversations, messages, conversation_states, conversation_memories'
\echo 'Ready for application startup'
