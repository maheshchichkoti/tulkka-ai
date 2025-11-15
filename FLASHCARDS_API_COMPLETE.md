# 📱 Flashcards API - Complete Reference for Frontend

This document maps **every API endpoint** to your frontend screens. Copy any URL directly into your code.

---

## 🎯 Frontend Flow → API Mapping

### Screen 1: Word Lists (List View)

**What it shows:** Scrollable list of word lists with name, word count, favorite star, and + button

| Action                          | API Call                                 |
| ------------------------------- | ---------------------------------------- |
| Load lists on screen open       | `GET /v1/word-lists?page=1&limit=20`     |
| Tap + button to create new list | `POST /v1/word-lists`                    |
| Tap star to favorite/unfavorite | `POST /v1/word-lists/{list_id}/favorite` |
| Tap row to open detail          | Navigate to Screen 2 with `list_id`      |

---

### Screen 2: Word List Detail

**What it shows:** List title at top, vertical list of words (word + translation + star), + button to add word, "Start Practice" button

| Action                           | API Call                                                 |
| -------------------------------- | -------------------------------------------------------- |
| Load list + words on screen open | `GET /v1/word-lists/{list_id}?include=words`             |
| Tap + button to add new word     | `POST /v1/word-lists/{list_id}/words`                    |
| Tap star on a word               | `POST /v1/word-lists/{list_id}/words/{word_id}/favorite` |
| Tap "Start Practice" button      | `POST /v1/flashcards/sessions` → Navigate to Screen 3    |
| Edit list name/description       | `PATCH /v1/word-lists/{list_id}`                         |
| Delete list                      | `DELETE /v1/word-lists/{list_id}`                        |

---

### Screen 3: Flashcards Practice

**What it shows:** Single card (word → flip → translation), progress "3 of 10", "Got it" / "Need practice" buttons

| Action                        | API Call                                                                                                                   |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Start session (from Screen 2) | `POST /v1/flashcards/sessions` with `{"wordListId": "..."}`                                                                |
| Tap "Got it"                  | `POST /v1/flashcards/sessions/{session_id}/results` with `{"wordId":"...","isCorrect":true,"timeSpent":2500,"attempts":1}` |
| Tap "Need practice"           | `POST /v1/flashcards/sessions/{session_id}/results` with `{"isCorrect":false}`                                             |
| Finish all cards              | `POST /v1/flashcards/sessions/{session_id}/complete` → Navigate to Screen 4                                                |

---

### Screen 4: Flashcards Summary

**What it shows:** Total correct, total incorrect, accuracy %, list of missed words, "Retry Incorrect" button

| Action                                  | API Call                                                                                                          |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Load summary (after completing session) | Use data from `POST /v1/flashcards/sessions/{session_id}/complete` response                                       |
| Tap "Retry Incorrect"                   | `POST /v1/flashcards/sessions` with `{"wordListId":"...","selectedWordIds":["id1","id2"]}` (only incorrect words) |

---

### Screen 5: Flashcards Stats (Optional)

**What it shows:** Total sessions, total studied words, average accuracy, line chart

| Action                    | API Call                      |
| ------------------------- | ----------------------------- |
| Load stats on screen open | `GET /v1/flashcards/stats/me` |

---

## 📋 Complete API Reference

### Base URL

```
http://localhost:8000/v1
```

Replace with production URL when deploying.

### Authentication

All requests require:

```
Authorization: Bearer <JWT_TOKEN>
```

---

## 1️⃣ Word Lists APIs

### 1.1 Get All Word Lists

```http
GET /v1/word-lists?page=1&limit=20
```

**Response:**

```json
{
  "data": [
    {
      "id": "wl_123",
      "user_id": "user_456",
      "name": "Unit 5 Vocabulary",
      "description": "Words for Unit 5",
      "is_favorite": false,
      "word_count": 12,
      "created_at": "2025-11-15T10:30:00Z",
      "updated_at": "2025-11-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 1
  }
}
```

**Copy-paste cURL:**

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:8000/v1/word-lists?page=1&limit=20"
```

---

### 1.2 Create Word List

```http
POST /v1/word-lists
Content-Type: application/json

{
  "name": "My New List",
  "description": "Optional description"
}
```

**Response:** `201 Created` + word list object

**Copy-paste cURL:**

```bash
curl -X POST http://localhost:8000/v1/word-lists \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"My New List","description":"Optional description"}'
```

---

### 1.3 Get Word List with Words

```http
GET /v1/word-lists/{list_id}?include=words&page=1&limit=100
```

**Response:**

```json
{
  "id": "wl_123",
  "name": "Unit 5 Vocabulary",
  "description": "Words for Unit 5",
  "is_favorite": false,
  "word_count": 12,
  "words": [
    {
      "id": "w_789",
      "list_id": "wl_123",
      "word": "present perfect",
      "translation": "الحال التام",
      "notes": "Used for past actions with present relevance",
      "difficulty": "intermediate",
      "is_favorite": false,
      "practice_count": 5,
      "correct_count": 4,
      "accuracy": 80,
      "last_practiced": "2025-11-15T10:30:00Z",
      "created_at": "2025-11-15T10:30:00Z",
      "updated_at": "2025-11-15T10:30:00Z"
    }
  ],
  "created_at": "2025-11-15T10:30:00Z",
  "updated_at": "2025-11-15T10:30:00Z"
}
```

---

### 1.4 Update Word List

```http
PATCH /v1/word-lists/{list_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "description": "Updated description",
  "isFavorite": true
}
```

**Response:** `200 OK` + updated word list

---

### 1.5 Delete Word List

```http
DELETE /v1/word-lists/{list_id}
```

**Response:** `204 No Content` (even if already deleted)

---

### 1.6 Toggle List Favorite

```http
POST /v1/word-lists/{list_id}/favorite
Content-Type: application/json

{
  "isFavorite": true
}
```

**Response:**

```json
{
  "ok": true,
  "isFavorite": true
}
```

---

## 2️⃣ Words APIs

### 2.1 Add Word to List

```http
POST /v1/word-lists/{list_id}/words
Content-Type: application/json

{
  "word": "present perfect",
  "translation": "الحال التام",
  "notes": "Used for past actions with present relevance",
  "difficulty": "intermediate"
}
```

**Response:** `201 Created` + word object

**Copy-paste cURL:**

```bash
curl -X POST http://localhost:8000/v1/word-lists/wl_123/words \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"word":"present perfect","translation":"الحال التام","notes":"Grammar tense","difficulty":"intermediate"}'
```

---

### 2.2 Update Word

```http
PATCH /v1/word-lists/{list_id}/words/{word_id}
Content-Type: application/json

{
  "notes": "Updated note",
  "difficulty": "advanced",
  "isFavorite": true
}
```

**Response:** `200 OK` + updated word

---

### 2.3 Delete Word

```http
DELETE /v1/word-lists/{list_id}/words/{word_id}
```

**Response:** `204 No Content`

---

### 2.4 Toggle Word Favorite

```http
POST /v1/word-lists/{list_id}/words/{word_id}/favorite
Content-Type: application/json

{
  "isFavorite": false
}
```

**Response:**

```json
{
  "ok": true,
  "isFavorite": false
}
```

---

## 3️⃣ Flashcard Session APIs

### 3.1 Start Flashcard Session

```http
POST /v1/flashcards/sessions
Content-Type: application/json
Idempotency-Key: <optional-uuid>

{
  "wordListId": "wl_123",
  "selectedWordIds": ["w_789", "w_790"]  // optional - if omitted, uses all words
}
```

**Response:** `201 Created`

```json
{
  "id": "fs_abc123",
  "wordListId": "wl_123",
  "words": [
    {
      "id": "w_789",
      "word": "present perfect",
      "translation": "الحال التام",
      "notes": "Grammar tense",
      "isFavorite": false,
      "practiceCount": 5,
      "correctCount": 4,
      "accuracy": 80,
      "lastPracticed": "2025-11-15T10:30:00Z",
      "createdAt": "2025-11-15T10:30:00Z",
      "updatedAt": "2025-11-15T10:30:00Z"
    }
  ],
  "progress": {
    "current": 0,
    "total": 10,
    "correct": 0,
    "incorrect": 0
  },
  "startedAt": "2025-11-15T10:30:00Z",
  "completedAt": null
}
```

**Copy-paste cURL:**

```bash
curl -X POST http://localhost:8000/v1/flashcards/sessions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"wordListId":"wl_123"}'
```

---

### 3.2 Get Session Details

```http
GET /v1/flashcards/sessions/{session_id}
```

**Response:** Same structure as start session response

---

### 3.3 Record Flashcard Result

```http
POST /v1/flashcards/sessions/{session_id}/results
Content-Type: application/json
Idempotency-Key: <optional-uuid>

{
  "wordId": "w_789",
  "isCorrect": true,
  "timeSpent": 2500,
  "attempts": 1
}
```

**Response:** `200 OK`

```json
{
  "ok": true
}
```

**Frontend Logic:**

- User taps "Got it" → send `"isCorrect": true`
- User taps "Need practice" → send `"isCorrect": false`
- Track time from card flip to button tap → send as `timeSpent` (milliseconds)

**Copy-paste cURL:**

```bash
curl -X POST http://localhost:8000/v1/flashcards/sessions/fs_abc123/results \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"wordId":"w_789","isCorrect":true,"timeSpent":2500,"attempts":1}'
```

---

### 3.4 Complete Session

```http
POST /v1/flashcards/sessions/{session_id}/complete
Content-Type: application/json

{
  "progress": {
    "current": 10,
    "total": 10,
    "correct": 8,
    "incorrect": 2
  }
}
```

**Response:** `200 OK`

```json
{
  "ok": true,
  "session": {
    "id": "fs_abc123",
    "status": "completed",
    "correct": 8,
    "incorrect": 2,
    "completedAt": "2025-11-15T10:45:00Z"
  }
}
```

**Frontend Logic:**

- Call this when user finishes all cards
- Use response data to populate Summary screen
- Extract incorrect word IDs for "Retry Incorrect" feature

---

### 3.5 Get User Stats

```http
GET /v1/flashcards/stats/me
```

**Response:**

```json
{
  "totals": {
    "total_sessions": 15,
    "completed_sessions": 12,
    "avg_score": 85.5,
    "total_correct": 120,
    "total_incorrect": 25
  }
}
```

**Frontend Logic:**

- Display on Stats screen
- Calculate accuracy: `(total_correct / (total_correct + total_incorrect)) * 100`

---

## 🔐 Authentication Notes

### Dev Mode (Testing)

If backend is running with `ENVIRONMENT=development`, auth is bypassed. Any request works.

### Production Mode

1. User logs in → receives JWT token
2. Store token securely (keychain/secure storage)
3. Include in every request: `Authorization: Bearer <token>`
4. Handle 401 responses → redirect to login

---

## 🎨 Frontend Implementation Tips

### Word Lists Screen

```javascript
// On screen load
const response = await fetch(
  "http://localhost:8000/v1/word-lists?page=1&limit=20",
  {
    headers: { Authorization: `Bearer ${token}` },
  }
);
const { data: wordLists } = await response.json();

// On tap star
await fetch(`http://localhost:8000/v1/word-lists/${listId}/favorite`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ isFavorite: !currentFavoriteStatus }),
});
```

### Word List Detail Screen

```javascript
// On screen load
const response = await fetch(
  `http://localhost:8000/v1/word-lists/${listId}?include=words`,
  { headers: { Authorization: `Bearer ${token}` } }
);
const wordList = await response.json();
```

### Flashcards Practice Screen

```javascript
// Start session
const startResponse = await fetch(
  "http://localhost:8000/v1/flashcards/sessions",
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "Idempotency-Key": generateUUID(),
    },
    body: JSON.stringify({ wordListId: listId }),
  }
);
const session = await startResponse.json();

// On "Got it" tap
await fetch(
  `http://localhost:8000/v1/flashcards/sessions/${session.id}/results`,
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "Idempotency-Key": generateUUID(),
    },
    body: JSON.stringify({
      wordId: currentWord.id,
      isCorrect: true,
      timeSpent: timeElapsed,
      attempts: 1,
    }),
  }
);

// On finish
await fetch(
  `http://localhost:8000/v1/flashcards/sessions/${session.id}/complete`,
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      progress: {
        current: currentIndex,
        total: totalCards,
        correct: correctCount,
        incorrect: incorrectCount,
      },
    }),
  }
);
```

---

## ✅ Database Schema (Minimal - 5 Tables)

Your backend only needs these tables (see `schema_minimal_flashcards_only.sql`):

1. **word_lists** - stores list name, description, favorite status
2. **words** - stores word, translation, notes, practice stats
3. **flashcard_sessions** - tracks practice sessions
4. **flashcard_results** - records each card result
5. **idempotency_keys** - prevents duplicate requests

**Total: 5 tables** (not 34!)

---

## 🚀 Ready to Integrate

All endpoints are tested and working. The backend dev can:

1. Run `schema_minimal_flashcards_only.sql` in MySQL
2. Start the server: `python main.py`
3. Copy any cURL example above into Postman
4. Frontend can integrate directly using the code snippets

**No other game tables needed** unless you add spelling/cloze/grammar/sentence features later.
