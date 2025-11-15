# 📘 Flashcards & Word Lists API Reference

This guide covers every `/v1/word-lists/...` and `/v1/flashcards/...` endpoint that the backend already exposes. The backend developer can copy any example directly into Postman/cURL.

## ✅ Base Setup

| Item        | Value                                                                         |
| ----------- | ----------------------------------------------------------------------------- |
| Base URL    | `http://localhost:8000/v1` (replace with production host)                     |
| Auth        | `Authorization: Bearer <JWT_TOKEN>` (required for all routes)                 |
| Idempotency | Optional `Idempotency-Key` header on POST routes that create results/sessions |

---

## 1. Word Lists

### 1.1 List Word Lists

- **Method / Path:** `GET /v1/word-lists`
- **Query params:** `page` (default 1), `limit` (default 20), `classId` (optional)
- **Sample request:**

```bash
curl -H "Authorization: Bearer <JWT>" \
     "http://localhost:8000/v1/word-lists?page=1&limit=20"
```

### 1.2 Create Word List

- **Method / Path:** `POST /v1/word-lists`
- **Body schema (`WordListCreate`):**

```json
{
  "name": "Unit 5 Vocabulary",
  "description": "Words for Unit 5",
  "classId": "class_123" // optional
}
```

- **Sample request:**

```bash
curl -X POST http://localhost:8000/v1/word-lists \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Unit 5 Vocabulary","description":"Words for Unit 5"}'
```

### 1.3 Get Word List (with optional words)

- **Method / Path:** `GET /v1/word-lists/{list_id}`
- **Query params:** `include=words`, `page`, `limit`

### 1.4 Update Word List

- **Method / Path:** `PATCH /v1/word-lists/{list_id}`
- **Body schema (`WordListUpdate` – partial fields):**

```json
{
  "name": "Updated name",
  "description": "Optional description",
  "isFavorite": true
}
```

### 1.5 Delete Word List (idempotent)

- **Method / Path:** `DELETE /v1/word-lists/{list_id}`
- Always returns 204 even if already deleted.

### 1.6 Toggle Word List Favorite

- **Method / Path:** `POST /v1/word-lists/{list_id}/favorite`
- **Body:** `{ "isFavorite": true }` (defaults to `true` if omitted)

---

## 2. Words inside a List

### 2.1 Add Word

- **Method / Path:** `POST /v1/word-lists/{list_id}/words`
- **Body schema (`WordCreate`):**

```json
{
  "word": "present perfect",
  "translation": "ألْحال التّام",
  "notes": "Used for past actions with present relevance",
  "difficulty": "intermediate"
}
```

### 2.2 Update Word

- **Method / Path:** `PATCH /v1/word-lists/{list_id}/words/{word_id}`
- **Body schema (`WordUpdate` – partial):**

```json
{ "notes": "New note", "difficulty": "advanced", "isFavorite": true }
```

### 2.3 Delete Word (idempotent)

- **Method / Path:** `DELETE /v1/word-lists/{list_id}/words/{word_id}`
- Returns 204 even if word already removed.

### 2.4 Toggle Word Favorite

- **Method / Path:** `POST /v1/word-lists/{list_id}/words/{word_id}/favorite`
- **Body:** `{ "isFavorite": false }`

---

## 3. Flashcard Sessions

### 3.1 Start Session

- **Method / Path:** `POST /v1/flashcards/sessions`
- **Headers:** `Idempotency-Key: <uuid>` (recommended)
- **Body (`StartSessionRequest`):**

```json
{
  "wordListId": "<list_id>",
  "selectedWordIds": ["<word_id1>", "<word_id2>"] // optional
}
```

### 3.2 Get Session Details

- **Method / Path:** `GET /v1/flashcards/sessions/{session_id}`
- Returns session metadata, progress, and full word list with accuracy stats.

### 3.3 Record Result

- **Method / Path:** `POST /v1/flashcards/sessions/{session_id}/results`
- **Headers:** `Idempotency-Key` (optional)
- **Body (`PracticeResultRequest`):**

```json
{
  "wordId": "<word_id>",
  "isCorrect": true,
  "timeSpent": 2500,
  "attempts": 1
}
```

### 3.4 Complete Session

- **Method / Path:** `POST /v1/flashcards/sessions/{session_id}/complete`
- **Body (`CompleteSessionRequest` – optional progress override):**

```json
{
  "progress": {
    "current": 10,
    "total": 10,
    "correct": 9,
    "incorrect": 1
  }
}
```

### 3.5 User Flashcard Stats

- **Method / Path:** `GET /v1/flashcards/stats/me`
- Returns aggregate totals (sessions, scores, correct/incorrect counts) derived from `game_sessions` table.

---

## ✅ Notes for Backend / QA

1. **Authentication:** Every call requires a valid JWT (dev mode allows bypass via environment flag `ENVIRONMENT=development`).
2. **Idempotency:** Provide `Idempotency-Key` when creating sessions or recording results to safely retry without duplicates.
3. **Error Codes:**
   - `422` for validation issues (missing fields, wrong enum values).
   - `404` when requesting/deleting resources not owned by the user.
   - `204` on successful deletes (even if the resource was already gone).
4. **Timestamps:** Responses return ISO strings (UTC). MySQL stores `DATETIME` in UTC.
5. **Pagination:** Word list retrieval supports `page` + `limit`; include words by passing `?include=words`.

Copy any example into Postman, set the `Authorization` bearer token, and you can hit production immediately.
