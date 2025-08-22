-- Migration: Allow empty module content
-- Date: 2024-01-22
-- Description: Modify the modules table to allow NULL/empty content

-- Make the content column nullable
ALTER TABLE modules 
ALTER COLUMN content DROP NOT NULL;

-- Add a comment to document the change
COMMENT ON COLUMN modules.content IS 'Module content - can be empty for modules that will be populated dynamically';