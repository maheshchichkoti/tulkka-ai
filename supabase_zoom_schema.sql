-- Supabase Schema for Zoom Integration
-- Run this in your Supabase SQL Editor

-- Create zoom_summaries table
CREATE TABLE IF NOT EXISTS zoom_summaries (
  id BIGSERIAL PRIMARY KEY,
  meeting_id TEXT NOT NULL,
  meeting_topic TEXT,
  teacher_email TEXT NOT NULL,
  meeting_date DATE NOT NULL,
  start_time TEXT,
  end_time TEXT,
  duration INTEGER DEFAULT 0,
  user_id TEXT NOT NULL,
  teacher_id TEXT NOT NULL,
  class_id TEXT NOT NULL,
  recording_urls JSONB DEFAULT '[]'::jsonb,
  transcript TEXT,
  transcript_url TEXT,
  status TEXT DEFAULT 'pending_transcript',
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_zoom_summaries_user ON zoom_summaries(user_id, teacher_id, class_id);
CREATE INDEX IF NOT EXISTS idx_zoom_summaries_date ON zoom_summaries(meeting_date);
CREATE INDEX IF NOT EXISTS idx_zoom_summaries_status ON zoom_summaries(status);
CREATE INDEX IF NOT EXISTS idx_zoom_summaries_meeting ON zoom_summaries(meeting_id);

-- Create lesson_exercises table
CREATE TABLE IF NOT EXISTS lesson_exercises (
  id BIGSERIAL PRIMARY KEY,
  zoom_summary_id BIGINT REFERENCES zoom_summaries(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  teacher_id TEXT NOT NULL,
  class_id TEXT NOT NULL,
  lesson_number INTEGER DEFAULT 1,
  exercises JSONB NOT NULL,
  generated_at TIMESTAMPTZ DEFAULT NOW(),
  status TEXT DEFAULT 'pending_approval',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for lesson_exercises
CREATE INDEX IF NOT EXISTS idx_lesson_exercises_zoom ON lesson_exercises(zoom_summary_id);
CREATE INDEX IF NOT EXISTS idx_lesson_exercises_user ON lesson_exercises(user_id, class_id);
CREATE INDEX IF NOT EXISTS idx_lesson_exercises_status ON lesson_exercises(status);

-- Enable Row Level Security (RLS)
ALTER TABLE zoom_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE lesson_exercises ENABLE ROW LEVEL SECURITY;

-- Create policies (adjust based on your auth setup)
-- For now, allow all operations (you can restrict this later)
CREATE POLICY "Allow all operations on zoom_summaries" ON zoom_summaries
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on lesson_exercises" ON lesson_exercises
  FOR ALL USING (true) WITH CHECK (true);

-- Add helpful comments
COMMENT ON TABLE zoom_summaries IS 'Stores Zoom recording metadata and transcripts from n8n workflow';
COMMENT ON TABLE lesson_exercises IS 'Stores AI-generated exercises from Zoom transcripts';

COMMENT ON COLUMN zoom_summaries.status IS 'Values: pending_transcript, pending_processing, completed, failed';
COMMENT ON COLUMN lesson_exercises.status IS 'Values: pending_approval, approved, rejected';
