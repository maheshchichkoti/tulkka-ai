# 📊 Supabase Schema Alignment

## Current Supabase Schema vs Code Usage

### ✅ zoom_summaries Table

Your actual Supabase schema has these columns:

```sql
CREATE TABLE zoom_summaries (
  -- Primary Key
  id BIGSERIAL PRIMARY KEY,

  -- Meeting Info (from API payload)
  meeting_id TEXT,                    -- Optional, from Zoom
  meeting_topic TEXT,                 -- From payload or default
  teacher_email TEXT NOT NULL,        -- REQUIRED
  meeting_date DATE NOT NULL,         -- REQUIRED
  start_time TEXT,                    -- REQUIRED for duplicate detection
  end_time TEXT,
  duration INTEGER DEFAULT 0,

  -- User/Class IDs (from API payload)
  user_id TEXT NOT NULL,              -- REQUIRED
  teacher_id TEXT NOT NULL,           -- REQUIRED
  class_id TEXT NOT NULL,             -- REQUIRED
  lesson_number INTEGER DEFAULT 1,    -- REQUIRED

  -- Recording Data (populated by worker)
  recording_urls JSONB DEFAULT '[]',
  transcript TEXT,                    -- Populated after transcription
  transcript_url TEXT,

  -- Processing Status
  status TEXT DEFAULT 'pending_transcript',
  error_message TEXT,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  -- Legacy/n8n fields (keep for compatibility)
  meeting_time TEXT,
  time_range TEXT,
  audio_file_name TEXT,
  audio_file_size_mb NUMERIC,

  -- Transcription Metadata
  transcript_length INTEGER,
  transcript_source TEXT,             -- 'zoom_native_transcript' or 'assemblyai'
  transcription_status TEXT,

  -- Processing Metadata (n8n compatibility)
  processing_mode TEXT,
  transcription_service TEXT,
  summarization_service TEXT,
  processing_started_at TIMESTAMPTZ,
  processing_completed_at TIMESTAMPTZ,
  processing_metadata JSONB,
  transcription_metadata JSONB,

  -- Worker Management
  processing_attempts INTEGER DEFAULT 0,
  last_error TEXT,
  next_retry_at BIGINT,
  claimed_at TIMESTAMPTZ,
  processed_at TIMESTAMPTZ
);
```

### ✅ lesson_exercises Table

**Actual Supabase Schema (Minimal):**

```sql
CREATE TABLE lesson_exercises (
  id BIGSERIAL PRIMARY KEY,
  zoom_summary_id BIGINT REFERENCES zoom_summaries(id),
  user_id TEXT NOT NULL,
  teacher_id TEXT NOT NULL,
  class_id TEXT NOT NULL,
  generated_at TIMESTAMPTZ DEFAULT NOW(),
  exercises JSONB NOT NULL,           -- Contains all exercise types + counts
  status TEXT DEFAULT 'pending_approval'
);
```

**❌ Columns that DON'T exist (removed from code):**

- `teacher_email` - Not in lesson_exercises (only in zoom_summaries)
- `metadata` - Embedded inside `exercises` JSON instead
- `lesson_id` - Uses `zoom_summary_id` instead

---

## 🔄 Status Flow Alignment

### n8n Status Values:

- `pending_transcript` → Initial state
- `awaiting_exercises` → Transcript ready, exercises pending
- `completed` → Fully processed

### Our Worker Status Values (Aligned):

- `pending` → Queued for processing
- `processing` → Worker claimed and processing
- `awaiting_exercises` → Transcript ready, exercises pending (matches n8n)
- `completed` → Exercises generated and stored (matches n8n)
- `failed` → Processing failed after retries

---

## 📝 Code Alignment

### API Payload → Supabase Insert

**API receives:**

```json
{
  "teacherEmail": "teacher@example.com",
  "date": "2025-11-24",
  "startTime": "14:00",
  "endTime": "15:30",
  "user_id": "student_123",
  "teacher_id": "teacher_456",
  "class_id": "class_789",
  "lesson_number": 1,
  "meetingId": "89349399406",
  "meetingTopic": "English Grammar"
}
```

**Code inserts into zoom_summaries:**

```python
zoom_summary_row = {
    'user_id': payload.user_id,           # ✅ Required
    'teacher_id': payload.teacher_id,     # ✅ Required
    'class_id': payload.class_id,         # ✅ Required
    'teacher_email': payload.teacherEmail, # ✅ Required
    'meeting_date': payload.date,         # ✅ Required
    'start_time': payload.startTime,      # ✅ Required (for duplicate detection)
    'end_time': payload.endTime,          # ✅ Optional
    'meeting_topic': payload.meetingTopic or f"Class {payload.class_id}",
    'lesson_number': payload.lesson_number, # ✅ Required
    'status': 'pending',                  # ✅ Initial status
    'processing_attempts': 0,
    'created_at': utc_now_iso()
}

# Optional fields
if payload.meetingId:
    zoom_summary_row['meeting_id'] = payload.meetingId
```

### Worker → Supabase Update

**After transcription:**

```python
update_payload = {
    "transcript": transcript_text,
    "transcript_length": len(transcript_text),
    "transcript_source": "zoom_native_transcript",  # or "assemblyai"
    "transcription_status": "completed",
    "status": "awaiting_exercises",                 # ✅ Matches n8n
    "processing_completed_at": utc_now_iso()
}
```

**After exercise generation:**

```python
# If successful
status = "completed"

# If failed
status = "awaiting_exercises"  # Keep transcript, retry exercises later
```

### Orchestrator → lesson_exercises Insert

**Payload structure (aligned with schema):**

```python
payload = {
    "zoom_summary_id": source_row.get("id"),  # ✅ FK to zoom_summaries
    "user_id": source_row.get("user_id"),     # ✅ Copied from zoom_summaries
    "teacher_id": source_row.get("teacher_id"), # ✅ Copied from zoom_summaries
    "class_id": source_row.get("class_id"),   # ✅ Copied from zoom_summaries
    "generated_at": utc_now_iso(),
    "exercises": {                             # ✅ All data in JSON
        "flashcards": [...],
        "cloze": [...],
        "grammar": [...],
        "sentence": [...],
        "counts": {                            # ✅ Embedded counts
            "flashcards": 15,
            "cloze": 8,
            "grammar": 10,
            "sentence": 7
        },
        "transcript_length": 18618             # ✅ Embedded metadata
    },
    "status": "pending_approval"
}
```

---

## 🔍 Duplicate Detection

**Logic:**

```python
# Check if lesson already exists (allows multiple lessons per day)
existing = supabase.fetch_zoom_summary(
    class_id=payload.class_id,
    meeting_date=payload.date,
    start_time=payload.startTime  # ✅ Includes time for uniqueness
)
```

**SQL equivalent:**

```sql
SELECT * FROM zoom_summaries
WHERE class_id = 'class_789'
  AND meeting_date = '2025-11-24'
  AND start_time = '14:00'
ORDER BY created_at DESC
LIMIT 1;
```

---

## 🗑️ Unused Fields (Safe to Ignore)

These fields exist in Supabase but aren't actively used by our code:

- `meeting_time` - Legacy n8n field
- `time_range` - Legacy n8n field
- `audio_file_name` - Legacy n8n field
- `audio_file_size_mb` - Legacy n8n field
- `processing_mode` - Legacy n8n field
- `transcription_service` - Legacy n8n field
- `summarization_service` - Legacy n8n field
- `transcription_metadata` - Legacy n8n field
- `next_retry_at` - Not currently used (could be added for scheduled retries)

**These are kept for backward compatibility with n8n data.**

---

## ✅ Schema Validation Checklist

- [x] All required fields populated by API
- [x] Status values match n8n conventions
- [x] Duplicate detection includes `start_time`
- [x] `lesson_exercises` payload matches actual schema
- [x] No references to non-existent columns (`teacher_email`, `metadata`, `lesson_id`)
- [x] Worker updates status correctly (`awaiting_exercises` → `completed`)
- [x] Retry logic uses `processing_attempts` field
- [x] Timestamps use `utc_now_iso()` consistently

---

## 🎯 Key Differences from n8n

| Aspect           | n8n                  | Our System                   |
| ---------------- | -------------------- | ---------------------------- |
| Initial status   | `pending_transcript` | `pending`                    |
| Transcript ready | `awaiting_exercises` | `awaiting_exercises` ✅      |
| Fully done       | `completed`          | `completed` ✅               |
| Recording fetch  | n8n webhook          | Worker fetches via Zoom API  |
| Transcription    | n8n workflow         | Worker + AssemblyAI fallback |
| Exercise gen     | n8n workflow         | Worker + AI orchestrator     |
| Storage          | Supabase             | Supabase ✅                  |

---

## 📊 Example Data Comparison

### n8n Row (from your example):

```json
{
  "id": 10,
  "meeting_id": "89349399406",
  "meeting_topic": "16:00 IST",
  "teacher_email": "iamyoursoncompletely@gmail.com",
  "meeting_date": "2025-11-18",
  "start_time": null,
  "status": "awaiting_exercises",
  "transcript": "Teacher Philip: Hello! Sohel: Hello!...",
  "transcript_length": 18618,
  "transcript_source": "zoom_native_transcript",
  "transcription_status": "completed"
}
```

### Our System Row (equivalent):

```json
{
  "id": 25,
  "meeting_id": "89349399406",
  "meeting_topic": "English Grammar Lesson",
  "teacher_email": "teacher@example.com",
  "meeting_date": "2025-11-24",
  "start_time": "14:00",
  "status": "completed",
  "transcript": "Hello students. Today we will learn...",
  "transcript_length": 18618,
  "transcript_source": "zoom_native_transcript",
  "transcription_status": "completed",
  "user_id": "student_123",
  "teacher_id": "teacher_456",
  "class_id": "class_789",
  "lesson_number": 1
}
```

**Key differences:**

- ✅ We populate `start_time` for duplicate detection
- ✅ We include `user_id`, `teacher_id`, `class_id` (required by backend)
- ✅ We use `completed` status when exercises are generated

---

## 🚀 Production Ready

Your schema is now **fully aligned** with:

- ✅ Actual Supabase table structure
- ✅ n8n data format (backward compatible)
- ✅ Backend requirements (user_id, teacher_id, class_id)
- ✅ Worker processing flow
- ✅ No column mismatch errors

**All schema-related errors are fixed!** 🎉
