-- Migration: Add ai_triggered column to classes table
-- Purpose: Track which classes have been sent to AI processing to prevent duplicates
-- Date: 2025-11-24

-- Add the column if it doesn't exist
ALTER TABLE classes 
ADD COLUMN IF NOT EXISTS ai_triggered TINYINT(1) NOT NULL DEFAULT 0 
COMMENT 'Flag to track if class has been sent to AI processing (0=not triggered, 1=triggered)';

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_classes_ai_triggered 
ON classes(status, ai_triggered, meeting_end);

-- Optionally: Mark all existing 'ended' classes as already triggered if you don't want to reprocess them
-- Uncomment the line below if you want to skip historical classes:
-- UPDATE classes SET ai_triggered = 1 WHERE status = 'ended' AND meeting_end IS NOT NULL;
