-- Migration: Staged Execution Redesign
-- Replaces BEFORE/AFTER timing system with staged execution pipeline
-- Date: 2025-01-28

-- Create ConversationState table for dedicated state storage
CREATE TABLE conversation_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    module_id UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    execution_stage VARCHAR(20) NOT NULL CHECK (execution_stage IN ('stage4', 'stage5')),
    
    -- State data
    variables JSONB NOT NULL DEFAULT '{}',
    execution_metadata JSONB DEFAULT '{}',
    executed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(conversation_id, module_id, execution_stage)
);

-- Add new execution context enum type
CREATE TYPE execution_context_enum AS ENUM ('IMMEDIATE', 'POST_RESPONSE', 'ON_DEMAND');

-- Add new fields to modules table
ALTER TABLE modules 
ADD COLUMN execution_context execution_context_enum DEFAULT 'ON_DEMAND',
ADD COLUMN requires_ai_inference BOOLEAN DEFAULT FALSE,
ADD COLUMN script_analysis_metadata JSONB DEFAULT '{}';

-- Note: Original timing and extra_data columns already removed in cleanup
-- All modules will default to ON_DEMAND execution context
-- No existing conversation state data to migrate

-- Make execution_context NOT NULL now that data is migrated
ALTER TABLE modules ALTER COLUMN execution_context SET NOT NULL;

-- Add check constraint for execution context
ALTER TABLE modules 
ADD CONSTRAINT valid_execution_context 
CHECK (execution_context IN ('IMMEDIATE', 'POST_RESPONSE', 'ON_DEMAND'));

-- Add comments for documentation
COMMENT ON TABLE conversation_states IS 
'Stores execution state for POST_RESPONSE modules across conversations';

COMMENT ON COLUMN conversation_states.execution_stage IS 
'Stage 4 (non-AI) or Stage 5 (AI-powered) post-response execution';

COMMENT ON COLUMN conversation_states.variables IS 
'Module script output variables stored as JSON for next conversation';

COMMENT ON COLUMN conversation_states.execution_metadata IS 
'Metadata about script execution (success, timing, errors, etc.)';

COMMENT ON COLUMN modules.execution_context IS 
'When module executes: immediate (during template resolution), post_response (after AI response), on_demand (triggered)';

COMMENT ON COLUMN modules.requires_ai_inference IS 
'Whether module script uses AI generation/reflection functions (auto-detected)';

COMMENT ON COLUMN modules.script_analysis_metadata IS 
'Metadata about script analysis (detected functions, complexity, etc.)';

-- Create indexes for conversation_states table
CREATE INDEX IF NOT EXISTS idx_conversation_states_conversation_id ON conversation_states(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_states_module_id ON conversation_states(module_id);
CREATE INDEX IF NOT EXISTS idx_conversation_states_executed_at ON conversation_states(executed_at);

-- Update existing indexes for modules
CREATE INDEX IF NOT EXISTS idx_modules_execution_context ON modules(execution_context);
CREATE INDEX IF NOT EXISTS idx_modules_ai_inference ON modules(requires_ai_inference);

-- Performance optimization: composite index for common queries
CREATE INDEX IF NOT EXISTS idx_modules_context_ai_active ON modules(execution_context, requires_ai_inference, is_active);

-- Note: Constraint to ensure conversation_states only for POST_RESPONSE modules
-- would require a trigger or application-level enforcement due to PostgreSQL subquery limitations