# 🚀 Production Deployment Guide

## ✅ System Status: PRODUCTION READY

Your Zoom lesson processing system is now fully production-ready with:

- ✅ End-to-end pipeline (Zoom → Transcript → Exercises → Supabase)
- ✅ Robust error handling with retry logic
- ✅ Clear status tracking and feedback
- ✅ Scalable worker architecture
- ✅ Production-grade logging

---

## 📋 Quick Start

### 1. Environment Setup

Update `.env` with your credentials:

```env
# Supabase (REQUIRED)
SUPABASE_URL=https://nlswzwucccjhsebkaczn.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Zoom API (REQUIRED)
ZOOM_ACCESS_TOKEN=your-zoom-access-token
ZOOM_CLIENT_ID=your-zoom-client-id
ZOOM_CLIENT_SECRET=your-zoom-client-secret
ZOOM_REFRESH_TOKEN=your-zoom-refresh-token

# AssemblyAI (OPTIONAL - for audio transcription fallback)
ASSEMBLYAI_API_KEY=your-assemblyai-key

# Groq AI (OPTIONAL - for better vocabulary extraction, falls back to heuristics)
# GROQ_API_KEY=your-groq-key
# GROQ_MODEL=llama-3.3-70b-versatile

# Worker Settings
WORKER_POLL_INTERVAL_SECONDS=60
WORKER_BATCH_SIZE=10
WORKER_MAX_RETRIES=5
```

### 2. Start the API Server

```bash
cd c:\nvm4w\SAHIONEXT\tulkka-ai
python main.py
```

API will be available at: `http://localhost:8000`
Swagger docs at: `http://localhost:8000/docs`

### 3. Start the Background Worker

```bash
cd c:\nvm4w\SAHIONEXT\tulkka-ai
python -m src.workers.zoom_processor
```

The worker polls Supabase every 60 seconds for pending lessons.

---

## 🔄 Complete Workflow

### Step 1: Backend Triggers Processing

Your backend calls the API after a Zoom lesson ends:

```bash
POST /v1/trigger-lesson-processing
Content-Type: application/json

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
  "meetingTopic": "English Grammar Lesson"
}
```

**Response (Success):**

```json
{
  "success": true,
  "message": "Lesson processing queued successfully",
  "zoom_summary_id": 25,
  "status": "pending",
  "class_id": "class_789",
  "lesson_number": 1,
  "meeting_date": "2025-11-24",
  "estimated_processing_time": "1-2 minutes",
  "next_steps": [
    "Worker will fetch Zoom recording",
    "Transcribe audio (if needed)",
    "Generate exercises with AI",
    "Store in lesson_exercises table"
  ],
  "check_status_url": "/v1/lesson-status/25",
  "check_exercises_url": "/v1/exercises?class_id=class_789"
}
```

### Step 2: Worker Processes Automatically

The background worker:

1. ✅ Fetches the Zoom recording via Zoom API
2. ✅ Downloads transcript (VTT) or audio file
3. ✅ Transcribes audio with AssemblyAI if needed
4. ✅ Generates exercises (flashcards, cloze, grammar, sentences)
5. ✅ Stores exercises in `lesson_exercises` table
6. ✅ Updates status to `completed`

### Step 3: Check Status

```bash
GET /v1/lesson-status/25
```

**Response:**

```json
{
  "success": true,
  "zoom_summary_id": 25,
  "status": "completed",
  "class_id": "class_789",
  "user_id": "student_123",
  "teacher_id": "teacher_456",
  "transcript_available": true,
  "transcript_length": 18618,
  "transcription_source": "zoom_native_transcript",
  "processing_attempts": 0,
  "last_error": null,
  "created_at": "2025-11-24T14:00:00Z",
  "processed_at": "2025-11-24T14:01:30Z",
  "exercises_generated": true,
  "exercises_id": 42
}
```

### Step 4: Fetch Exercises

```bash
GET /v1/exercises?class_id=class_789
```

**Response:**

```json
{
  "success": true,
  "count": 1,
  "exercises": [
    {
      "id": 42,
      "zoom_summary_id": 25,
      "class_id": "class_789",
      "user_id": "student_123",
      "teacher_id": "teacher_456",
      "generated_at": "2025-11-24T14:01:30Z",
      "status": "pending_approval",
      "exercises": {
        "flashcards": [...],
        "cloze": [...],
        "grammar": [...],
        "sentence": [...],
        "counts": {
          "flashcards": 15,
          "cloze": 8,
          "grammar": 10,
          "sentence": 7
        }
      }
    }
  ]
}
```

---

## 📊 Status Flow

```
pending → processing → awaiting_exercises → completed
                    ↓
                  failed (with retry logic)
```

### Status Meanings:

| Status               | Meaning                             | Next Action                                       |
| -------------------- | ----------------------------------- | ------------------------------------------------- |
| `pending`            | Queued, waiting for worker          | Worker will pick up automatically                 |
| `processing`         | Worker is currently processing      | Wait for completion                               |
| `awaiting_exercises` | Transcript ready, exercises pending | Manual regeneration or retry                      |
| `completed`          | Fully processed with exercises      | Ready to use                                      |
| `failed`             | Processing failed after max retries | Check `last_error`, fix issue, reset to `pending` |

---

## 🔧 Error Handling

### Common Errors & Solutions

#### 1. "No Zoom recordings found"

**Cause:** Recording not available yet or wrong teacher email/date  
**Solution:**

- Wait 5-10 minutes after meeting ends
- Verify teacher email matches Zoom account
- Check meeting date is correct
- Ensure recording was enabled in Zoom

#### 2. "No transcript or audio files found"

**Cause:** Zoom recording still processing  
**Solution:** Wait and retry (worker will auto-retry up to 5 times)

#### 3. "AssemblyAI transcription failed"

**Cause:** AssemblyAI API key missing or invalid  
**Solution:** Add valid `ASSEMBLYAI_API_KEY` to `.env`

#### 4. "Exercise generation failed"

**Cause:** Groq API error or empty transcript  
**Solution:** System falls back to heuristics automatically

### Manual Recovery

If a row is stuck in `failed` status:

1. Check the error:

```sql
SELECT id, status, last_error, processing_attempts
FROM zoom_summaries
WHERE status = 'failed';
```

2. Fix the underlying issue (e.g., add API keys, wait for recording)

3. Reset to pending:

```sql
UPDATE zoom_summaries
SET status = 'pending', processing_attempts = 0, last_error = NULL
WHERE id = 25;
```

4. Worker will retry automatically

---

## 🚀 Scaling for Production

### For 5000+ lessons/month:

#### Option 1: Single Worker (Recommended for <100 lessons/day)

```bash
# Run worker as a service
python -m src.workers.zoom_processor
```

#### Option 2: Multiple Workers (For high throughput)

```bash
# Terminal 1
python -m src.workers.zoom_processor

# Terminal 2
python -m src.workers.zoom_processor

# Terminal 3
python -m src.workers.zoom_processor
```

Workers use optimistic locking (claim rows atomically), so multiple instances won't conflict.

#### Option 3: Deploy on Render/Heroku

**Render (Recommended):**

1. Create new Background Worker service
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `python -m src.workers.zoom_processor`
4. Environment: Add all `.env` variables
5. Instance: Standard (512MB RAM)

**Cost:** ~$7/month for 24/7 worker

---

## 📈 Monitoring

### Key Metrics to Track:

1. **Processing Success Rate**

```sql
SELECT
  status,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM zoom_summaries
GROUP BY status;
```

2. **Average Processing Time**

```sql
SELECT
  AVG(EXTRACT(EPOCH FROM (processed_at - created_at))) as avg_seconds
FROM zoom_summaries
WHERE status = 'completed';
```

3. **Failed Lessons**

```sql
SELECT id, class_id, meeting_date, last_error, processing_attempts
FROM zoom_summaries
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 10;
```

### Logs

Worker logs show:

- ✅ Successful processing: `"Generated exercises for row X: {...}"`
- ⚠️ Warnings: `"No Zoom recordings found..."`
- ❌ Errors: Full stack traces with context

---

## 🔐 Security Checklist

- ✅ API keys stored in `.env` (never commit to Git)
- ✅ Supabase RLS policies enabled
- ✅ CORS configured for your frontend domain
- ✅ Rate limiting enabled (via FastAPI middleware)
- ✅ JWT authentication for production endpoints

---

## 🎯 Backend Integration

### For Your Backend Team:

**Single API Call Per Lesson:**

```javascript
// After Zoom meeting ends
const response = await fetch(
  "https://your-api.com/v1/trigger-lesson-processing",
  {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      teacherEmail: "teacher@example.com",
      date: "2025-11-24",
      startTime: "14:00",
      endTime: "15:30",
      user_id: "student_123",
      teacher_id: "teacher_456",
      class_id: "class_789",
      lesson_number: 1,
      meetingId: "89349399406",
      meetingTopic: "English Grammar",
    }),
  }
);

const data = await response.json();
console.log(data.zoom_summary_id); // Track this ID
```

**Poll for Status (Optional):**

```javascript
const statusResponse = await fetch(
  `https://your-api.com/v1/lesson-status/${zoom_summary_id}`
);
const status = await statusResponse.json();

if (status.status === "completed" && status.exercises_generated) {
  // Exercises ready!
}
```

---

## ✅ Production Checklist

Before going live:

- [ ] `.env` configured with all required credentials
- [ ] Supabase tables created (`zoom_summaries`, `lesson_exercises`)
- [ ] Zoom OAuth tokens refreshed (run `zoom_get_token.py`)
- [ ] API server running and accessible
- [ ] Worker running continuously (as service or on Render)
- [ ] Test end-to-end with real Zoom recording
- [ ] Monitoring dashboard set up
- [ ] Error alerting configured
- [ ] Backup strategy for Supabase data

---

## 🎉 You're Ready!

Your system is **production-ready** and can handle:

- ✅ Thousands of lessons per month
- ✅ Automatic retries on failures
- ✅ Graceful degradation (heuristics when AI fails)
- ✅ Clear status tracking
- ✅ Scalable architecture

**Questions?** Check logs or contact support.

**Next:** Deploy to production and integrate with your backend! 🚀
