# 📋 API Quick Reference Card

## Base URL

```
http://localhost:8000
```

---

## 🏥 Health & Docs

```bash
# Health Check
GET /v1/health

# API Documentation
GET /docs
```

---

## 📚 Lesson Processing

### Process Transcript

```bash
POST /v1/process
Content-Type: application/json

{
  "transcript": "Your lesson text",
  "lesson_number": 1,
  "user_id": "student_123",
  "class_id": "class_789"
}
```

### Process Zoom Lesson

```bash
POST /v1/process-zoom-lesson
Content-Type: application/json

{
  "user_id": "student_123",
  "teacher_id": "teacher_456",
  "class_id": "class_789",
  "date": "2025-10-16",
  "lesson_number": 1,
  "meeting_id": "optional",
  "start_time": "10:00",
  "end_time": "11:00",
  "teacher_email": "amit@tulkka.com"
}
```

### Get Exercises

```bash
GET /v1/exercises?class_id=class_789&user_id=student_123
```

---

## 📇 Word Lists

```bash
# List all word lists
GET /v1/word-lists?page=1&limit=10&search=animals&favorite=true

# Create word list
POST /v1/word-lists
{
  "name": "Animals",
  "description": "Animal vocabulary",
  "language": "en"
}

# Get word list
GET /v1/word-lists/{list_id}

# Update word list
PATCH /v1/word-lists/{list_id}
{
  "name": "Updated name",
  "description": "Updated description"
}

# Delete word list
DELETE /v1/word-lists/{list_id}

# Toggle favorite
POST /v1/word-lists/{list_id}/favorite
```

---

## 📝 Words

```bash
# Add word to list
POST /v1/word-lists/{list_id}/words
{
  "word": "cat",
  "translation": "gato",
  "pronunciation": "kat",
  "example_sentence": "The cat is sleeping"
}

# Update word
PATCH /v1/word-lists/{list_id}/words/{word_id}
{
  "translation": "el gato"
}

# Delete word
DELETE /v1/word-lists/{list_id}/words/{word_id}

# Toggle word favorite
POST /v1/word-lists/{list_id}/words/{word_id}/favorite
```

---

## 🎴 Flashcard Sessions

```bash
# Start session
POST /v1/flashcards/sessions
{
  "wordListId": "list-uuid",
  "settings": {
    "shuffle": true,
    "showTranslation": true
  }
}

# Get session
GET /v1/flashcards/sessions/{session_id}

# Record result
POST /v1/flashcards/sessions/{session_id}/result
{
  "wordId": "word-uuid",
  "isCorrect": true,
  "attempts": 1,
  "timeSpentMs": 3000
}

# Complete session
POST /v1/flashcards/sessions/{session_id}/complete
{
  "progress": {
    "current": 10,
    "total": 10,
    "correct": 8,
    "incorrect": 2
  }
}

# Get stats
GET /v1/flashcards/stats/me
```

---

## 🔤 Spelling

```bash
# Get spelling stats
GET /v1/spelling/stats/me
```

---

## 📄 Cloze (Fill-in-the-Blank)

```bash
# Get lessons
GET /v1/cloze/lessons?class_id=class_789

# Get stats
GET /v1/cloze/stats/me
```

---

## ✏️ Grammar

```bash
# Get lessons
GET /v1/grammar/lessons?class_id=class_789

# Get stats
GET /v1/grammar/stats/me
```

---

## 🔨 Sentence Builder

```bash
# Get lessons
GET /v1/sentence/lessons?class_id=class_789

# Get stats
GET /v1/sentence/stats/me
```

---

## 🔐 Authentication

### Development Mode

No authentication required when `ENVIRONMENT=development`

### Production Mode

Include JWT token in all requests:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8000/v1/word-lists
```

**Public endpoints** (no auth):

- `/v1/health`
- `/docs`
- `/openapi.json`

---

## 📊 Response Codes

| Code | Meaning                       |
| ---- | ----------------------------- |
| 200  | Success                       |
| 201  | Created                       |
| 204  | No Content (success, no body) |
| 400  | Bad Request                   |
| 401  | Unauthorized                  |
| 404  | Not Found                     |
| 500  | Internal Server Error         |

---

## 🧪 Testing

```bash
# Run full test suite
python test_all_apis.py

# Expected: 26/26 tests passing
```

---

## 🚀 Quick Start

```bash
# 1. Start server
python main.py

# 2. Test health
curl http://localhost:8000/v1/health

# 3. Process a lesson
curl -X POST http://localhost:8000/v1/process \
  -H "Content-Type: application/json" \
  -d '{"transcript":"Hello world","lesson_number":1}'

# 4. Create word list
curl -X POST http://localhost:8000/v1/word-lists \
  -H "Content-Type: application/json" \
  -d '{"name":"My List","language":"en"}'
```

---

## 📞 Need Help?

See `PRODUCTION_READY.md` for complete deployment guide.
