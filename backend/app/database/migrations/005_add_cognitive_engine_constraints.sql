-- Migration: Add Cognitive Engine Database Constraints
-- This migration adds constraints to ensure data integrity for the cognitive engine
-- Date: 2025-01-22

-- Add unique constraint for module names (required for @module_name references)
ALTER TABLE modules 
ADD CONSTRAINT unique_module_name UNIQUE (name);

-- Add check constraint for module name format (must start with letter, only lowercase/numbers/underscores, max 50 chars)
ALTER TABLE modules 
ADD CONSTRAINT valid_module_name_format 
CHECK (
  name ~ '^[a-z][a-z0-9_]{0,49}$' AND
  LENGTH(name) <= 50
);

-- Add unique constraint for persona names (prevent confusion with duplicate names)
ALTER TABLE personas 
ADD CONSTRAINT unique_persona_name UNIQUE (name);

-- Add check constraint for persona mode (only allow 'reactive' or 'autonomous')
ALTER TABLE personas 
ADD CONSTRAINT valid_persona_mode 
CHECK (mode IN ('reactive', 'autonomous'));

-- Add check constraint for loop frequency (must be a valid float for autonomous mode)
ALTER TABLE personas 
ADD CONSTRAINT valid_loop_frequency 
CHECK (
  loop_frequency IS NULL OR 
  (mode = 'autonomous' AND loop_frequency ~ '^[0-9]*\.?[0-9]+$' AND CAST(loop_frequency AS FLOAT) > 0)
);

-- Add indexes for performance on commonly searched fields
CREATE INDEX IF NOT EXISTS idx_modules_type ON modules (type);
CREATE INDEX IF NOT EXISTS idx_modules_active ON modules (is_active);
CREATE INDEX IF NOT EXISTS idx_personas_mode ON personas (mode);
CREATE INDEX IF NOT EXISTS idx_personas_active ON personas (is_active);

-- Comments for documentation
COMMENT ON CONSTRAINT unique_module_name ON modules IS 
'Ensures module names are unique for @module_name template resolution';

COMMENT ON CONSTRAINT valid_module_name_format ON modules IS 
'Enforces cognitive engine naming policy: start with letter, lowercase/numbers/underscores only, max 50 chars';

COMMENT ON CONSTRAINT unique_persona_name ON personas IS 
'Prevents duplicate persona names for better user experience';

COMMENT ON CONSTRAINT valid_persona_mode ON personas IS 
'Ensures only valid persona operating modes: reactive or autonomous';

COMMENT ON CONSTRAINT valid_loop_frequency ON personas IS 
'Validates loop frequency is a positive float when persona is in autonomous mode';