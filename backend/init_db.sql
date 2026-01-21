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
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
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
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
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

CREATE TRIGGER update_conversation_states_updated_at BEFORE UPDATE ON conversation_states
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversation_memories_updated_at BEFORE UPDATE ON conversation_memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

\echo '✓ Triggers created for automatic updated_at'

-- ============================================
-- Insert Default Data
-- ============================================

\echo '=== Inserting default data ==='

-- Insert default persona: Ava
INSERT INTO personas (name, description, template, mode, first_message, is_active)
VALUES (
    'Ava',
    'General purpose digital assistant.',
    E'You are Ava, a general purpose digital assistant.\n\n---\n\n@long_term_memory\n\nThese are the most recent messages we exchanged:\n@short_term_memory\n\n---',
    'reactive',
    'Hello! I''m Ava, your digital assistant. How can I help you today?',
    TRUE
);
\echo '✓ Default persona created: Ava'

-- Insert default module: short_term_memory
INSERT INTO modules (name, description, content, script, execution_context, type, is_active)
VALUES (
    'short_term_memory',
    'Provides recent conversation history context',
    '${history}',
    'history = ctx.get_recent_messages(30)',
    'IMMEDIATE',
    'ADVANCED',
    TRUE
);
\echo '✓ Default module created: short_term_memory'

-- Insert default module: long_term_memory
INSERT INTO modules (name, description, content, script, execution_context, type, is_active)
VALUES (
    'long_term_memory',
    'Maintains living narrative and episodic memories for long conversations',
    '${memories}',
    $$# Long-term memory module using living narrative + episodic memories
#
# This module maintains:
# 1. Living narrative (~800 tokens) - bounded self-updating summary
# 2. Recent episodes (5 × ~300 tokens) - compressed conversation segments
# 3. Total: ~2,300 tokens optimized for 8K context windows
#
# Works alongside @short_term_memory (last 20 verbatim messages)

# Constants
NARRATIVE_UPDATE_INTERVAL = 20  # Update narrative every N messages
MAX_EPISODES = 5  # Keep most recent 5 episodes
EPISODE_SIZE = 20  # Messages per episode
SHORT_TERM_COUNT = 20  # Messages in short-term (don't compress these)

# Get total message count
message_count = ctx.get_message_count()

# Handle test mode or conversations with too few messages
if message_count == 0:
    memories = """## LONG-TERM MEMORY (Test Mode)

This module requires a real conversation to function.

**What it does:**
- Living Narrative: ~800 token summary of entire conversation
- Episodes: 5 recent summaries (~300 tokens each)
- Updates every 20 new messages
- Total: ~2,300 tokens of compressed context

To see this in action, use in a conversation with 20+ messages."""

elif message_count <= SHORT_TERM_COUNT:
    memories = """## LONG-TERM MEMORY

Not enough messages yet for long-term compression.
This module activates after 20+ messages."""

else:
    # Initialize output
    output_parts = []

    # ==========================================================================
    # PART 1: LIVING NARRATIVE
    # ==========================================================================

    narrative = ctx.get_variable("living_narrative", None)
    last_update = ctx.get_variable("last_narrative_update", 0)
    messages_since_update = message_count - last_update

    # Update narrative if needed
    should_update = (narrative is None) or (messages_since_update >= NARRATIVE_UPDATE_INTERVAL)

    if should_update:
        # Get ALL compressible messages for narrative context
        # (everything except the last SHORT_TERM_COUNT messages)
        compressible_end = message_count - SHORT_TERM_COUNT

        # Get all compressible messages using the new range function
        recent_context = ctx.get_message_range(0, compressible_end)

        if narrative:
            # Update existing narrative
            instructions = """I am updating my living narrative summary of this ongoing conversation.

CURRENT NARRATIVE:
{narrative}

RECENT CONVERSATION CONTEXT:
{recent_context}

I will update the narrative to incorporate new developments while maintaining coherence.
Keep it concise (~800 tokens max). Focus on:
- Core themes and topics
- Key facts and insights
- Evolving context
- Important background

Return ONLY the updated narrative, no preamble.""".format(
                narrative=narrative,
                recent_context=recent_context
            )
        else:
            # Create initial narrative
            instructions = """I am creating a living narrative summary of this conversation.

CONVERSATION CONTEXT:
{recent_context}

I will create a concise narrative (~800 tokens max) that captures:
- Core themes and topics
- Key facts and insights
- Important context
- Nature of the interaction

Return ONLY the narrative, no preamble.""".format(
                recent_context=recent_context
            )

        try:
            new_narrative = ctx.reflect(instructions, role="assistant")
            ctx.set_variable("living_narrative", new_narrative)
            ctx.set_variable("last_narrative_update", message_count)
            narrative = new_narrative
        except Exception as e:
            ctx.log("Failed to update narrative: " + str(e))

    # Add narrative to output
    if narrative:
        output_parts.append("## LIVING NARRATIVE\n" + narrative)

    # ==========================================================================
    # PART 2: EPISODIC MEMORIES
    # ==========================================================================

    episodes = ctx.get_variable("episodes_cache", [])
    last_episode_end = ctx.get_variable("last_episode_end", 0)

    # Calculate compression boundary (exclude short-term messages)
    compressible_end = message_count - SHORT_TERM_COUNT
    messages_to_compress = compressible_end - last_episode_end

    # Create new episodes if we have enough messages
    if messages_to_compress >= EPISODE_SIZE:
        new_episodes_needed = int(messages_to_compress / EPISODE_SIZE)

        for i in range(new_episodes_needed):
            episode_start = last_episode_end + (i * EPISODE_SIZE)
            episode_end = episode_start + EPISODE_SIZE

            if episode_end > compressible_end:
                break

            # Get messages for this episode (specific range)
            episode_context = ctx.get_message_range(episode_start, episode_end)

            instructions = """I am summarizing this conversation segment into a concise episode (~300 tokens max).

CONVERSATION SEGMENT:
{episode_context}

I will focus on:
- Key points discussed
- Important decisions/conclusions
- Relevant context for future
- Notable developments

Return ONLY the summary, no preamble.""".format(
                episode_context=episode_context
            )

            try:
                summary = ctx.reflect(instructions, role="assistant")

                episodes.append({
                    "summary": summary,
                    "start_msg": episode_start,
                    "end_msg": episode_end,
                    "created_at": episode_end
                })

                last_episode_end = episode_end
            except Exception as e:
                ctx.log("Failed to create episode: " + str(e))
                break

        # Keep only recent episodes
        if len(episodes) > MAX_EPISODES:
            episodes = episodes[-MAX_EPISODES:]

        # Save state
        ctx.set_variable("episodes_cache", episodes)
        ctx.set_variable("last_episode_end", last_episode_end)

    # Add episodes to output
    if episodes:
        output_parts.append("\n## RECENT EPISODES")
        episode_num = 1
        for episode in reversed(episodes):
            output_parts.append("\n### Episode " + str(episode_num) + " (messages " + str(episode['start_msg']) + "-" + str(episode['end_msg']) + ")")
            output_parts.append(episode['summary'])
            episode_num = episode_num + 1

    # ==========================================================================
    # DEBUG INFO
    # ==========================================================================

    debug = """
---
[Long-term Memory Debug]
Total messages: {message_count}
Narrative: {narrative_status}
Episodes: {episodes_count}
Last episode: {last_episode_end}
Since narrative update: {messages_since_update}
Compressible: {compressible_end}
Next episode: {next_episode}
""".format(
        message_count=message_count,
        narrative_status='Present' if narrative else 'Not created',
        episodes_count=len(episodes),
        last_episode_end=last_episode_end,
        messages_since_update=messages_since_update,
        compressible_end=compressible_end,
        next_episode=last_episode_end + EPISODE_SIZE
    )

    output_parts.append(debug)

    # Set output variable for template substitution
    memories = "\n".join(output_parts)$$,
    'POST_RESPONSE',
    'ADVANCED',
    TRUE
);
\echo '✓ Default module created: long_term_memory'

-- ============================================
-- Completion
-- ============================================

\echo '=== Project 2501 Database Initialization Complete ==='
\echo 'Database: project2501'
\echo 'Schema version: Equivalent to migrations 001-008'
\echo 'Tables: personas, modules, conversations, messages, conversation_states, conversation_memories'
\echo 'Default data: 1 persona (Ava), 1 module (short_term_memory)'
\echo 'Ready for application startup'
