# Flashcards – Backend API Specification (TULKKA)

## Overview

This document specifies all backend APIs required to power the Games → Flashcards experience in the mobile app.
It is based on the current UI flows and code in:
- `app/games/flashcards.tsx`
- `services/api/flashcardService.ts` (client mocks used today)
- Shared Word Lists screen: `app/games/word-lists.tsx` (managing lists/words)

Primary use cases:
- Users browse their word lists and select one to practice (or a subset of words)
- Start a flashcard practice session using words from a list
- For each card, mark as “Got it” or “Need practice” (records a result)
- Complete a session and view results summaries (accuracy, counts)
- Manage lists and words (create/update/delete, toggle favorites)

## Definitions
- "Word": a vocabulary entry with `word`, `translation`, optional `notes`
- "Word List": a user-owned collection of `Word`
- "Flashcard Session": time-bounded practice over a list’s words

## High-level Flows

1) Select practice source
- App loads available Word Lists (names, counts)
- User picks a list (optionally a subset of words)

2) Start session
- App calls start-session with list id (+ optional subset)
- Backend returns ordered words and a session id

3) Per-card result
- For each word, app records a result (correct/incorrect, attempts, time)
- Backend updates per-word counters and session progress

4) Complete session
- App sends final progress; backend persists completion and returns summary

## Data Model (suggested)

Tables (indicative names):
- `word_lists(id, user_id, name, description, is_favorite, word_count, created_at, updated_at)`
- `words(id, list_id, word, translation, notes, is_favorite, practice_count, correct_count, accuracy, last_practiced, created_at, updated_at)`
- `flashcard_sessions(id, user_id, list_id, started_at, completed_at, progress_current, progress_total, correct, incorrect)`
- `flashcard_results(id, session_id, word_id, is_correct, attempts, time_spent_ms, created_at)`

Indexes:
- `word_lists(user_id, name)`
- `words(list_id, word)`
- `flashcard_results(session_id, word_id)` unique for last result if you want upsert-by-word

## Security & Auth
- All endpoints require Bearer JWT (except public assets if added later)
- Validate `user_id` from token matches list/session ownership
- Rate limit result writes and session creation to prevent abuse

## Validation Rules
- Word List
  - `name`: 1–120 chars
- Word
  - `word`: 1–120 chars, `translation`: 1–240 chars
- Session
  - `selectedWordIds` (when present) must belong to `wordListId`
  - `attempts` ≥ 1; `time_spent` ≥ 0 ms

## Error Codes (common)
- 400: `validation_error`, `unknown_word`, `unknown_list`, `not_in_list`
- 401: `unauthorized`
- 403: `forbidden`
- 404: `not_found`
- 409: `conflict`
- 429: `rate_limited`
- 500: `server_error`

## Endpoints

### 1) Word Lists

GET `/v1/word-lists`
- Query: `?page=1&limit=20&search=cats&favorite=true&sort=name|createdAt|updatedAt`
- Request headers
  - `Authorization: Bearer <jwt>`
  - `Accept-Language: <locale>` (optional)
- Response 200
```json
{
  "data": [
    {"id":"wl_1","name":"Basic Vocabulary","description":"","wordCount":10,"isFavorite":false,"createdAt":"...","updatedAt":"..."}
  ],
  "pagination": {"page":1,"limit":20,"total":2}
}
```
- Errors: 401, 429, 500

POST `/v1/word-lists`
- Body
```json
{"name":"Animals","description":"Common animal names"}
```
- Response 201 → WordList (without `words`)
- Errors: 400 (validation_error), 401, 409, 500

GET `/v1/word-lists/{listId}`
- Response 200 → WordList with `words` array (paginated optional: `?include=words&page=1&limit=100`)
- Errors: 401, 403, 404, 500

PATCH `/v1/word-lists/{listId}`
- Body (partial)
```json
{"name":"Updated","description":"...","isFavorite":true}
```
- Response 200 → WordList
- Errors: 400, 401, 403, 404, 409, 500

DELETE `/v1/word-lists/{listId}` → 204
- Errors: 401, 403, 404, 500

POST `/v1/word-lists/{listId}/favorite`
- Body `{ "isFavorite": true }` → 200 `{ "ok": true }`
- Errors: 400, 401, 403, 404, 500

### 2) Words (within a Word List)

POST `/v1/word-lists/{listId}/words`
- Body
```json
{"word":"Hello","translation":"مرحبا","notes":"Common greeting"}
```
- Response 201 → Word
- Errors: 400 (validation_error), 401, 403, 404, 409, 500

PATCH `/v1/word-lists/{listId}/words/{wordId}`
- Body (partial)
```json
{"word":"Hi","translation":"أهلاً","notes":"","isFavorite":true}
```
- Response 200 → Word
- Errors: 400, 401, 403, 404, 409, 500

DELETE `/v1/word-lists/{listId}/words/{wordId}` → 204
- Errors: 401, 403, 404, 500

POST `/v1/word-lists/{listId}/words/{wordId}/favorite`
- Body `{ "isFavorite": true }` → 200 `{ "ok": true }`
- Errors: 400, 401, 403, 404, 500

### 3) Flashcard Sessions

POST `/v1/flashcards/sessions`
- Purpose: Start a session for a list (optionally subset)
- Body
```json
{"wordListId":"wl_1","selectedWordIds":["w_1","w_2"]}
```
- Behavior: if `selectedWordIds` omitted, use all list words (ordered). Return words in practice order.
- Response 201 → FlashcardSession
- Full response example
```json
{
  "id": "fs_123",
  "wordListId": "wl_1",
  "words": [
    {
      "id": "w_1",
      "word": "Hello",
      "translation": "مرحبا",
      "notes": "Common greeting",
      "isFavorite": false,
      "practiceCount": 5,
      "correctCount": 4,
      "accuracy": 80,
      "lastPracticed": "2025-10-16T10:00:00Z",
      "createdAt": "2025-10-01T10:00:00Z",
      "updatedAt": "2025-10-16T10:00:00Z"
    }
  ],
  "progress": { "current": 0, "total": 10, "correct": 0, "incorrect": 0 },
  "startedAt": "2025-10-16T12:00:00Z",
  "completedAt": null
}
```
- Errors: 400 (`not_in_list` for wrong ids), 401, 403, 404 (`unknown_list`), 429, 500

GET `/v1/flashcards/sessions/{sessionId}`
- Response 200 → FlashcardSession (server progress if tracked)
- Errors: 401, 403, 404, 500

POST `/v1/flashcards/sessions/{sessionId}/results`
- Purpose: Record per-word result
- Body (PracticeResult)
```json
{"wordId":"w_1","isCorrect":true,"timeSpent":1200,"attempts":1}
```
- Response 200 `{ "ok": true }`
- Side effects (server):
  - `words.practice_count++`, `correct_count++` if correct
  - recompute `accuracy` = round(100 * correct_count / practice_count)
  - update `last_practiced`
  - optionally increment session progress (current, correct/incorrect)
- Errors: 400 (`unknown_word`, `not_in_list`, `validation_error`), 401, 403, 404 (unknown session), 409, 429, 500

POST `/v1/flashcards/sessions/{sessionId}/complete`
- Body (optional summary)
```json
{"progress":{"current":10,"total":10,"correct":8,"incorrect":2}}
```
- Response 200 → FlashcardSession with `completedAt`
- Full response example
```json
{
  "id": "fs_123",
  "wordListId": "wl_1",
  "words": [],
  "progress": { "current": 10, "total": 10, "correct": 8, "incorrect": 2 },
  "startedAt": "2025-10-16T12:00:00Z",
  "completedAt": "2025-10-16T12:30:00Z"
}
```
- Errors: 400, 401, 403, 404, 409, 500

### 4) Analytics (optional, recommended)

GET `/v1/flashcards/stats/me`
- Returns user-level aggregates for dashboards
- Response 200
```json
{
  "totals": {"sessions": 32, "wordsStudied": 540},
  "accuracy": {"overall": 78},
  "recent": [{"date":"2025-10-14","studied":40,"accuracy":82}]
}
```

## Error Shape
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Word list not found",
    "details": {"resourceId":"wl_404"}
  }
}
```

### Standard Success Wrapper (optional)
Some teams prefer a wrapper for all 2xx responses:
```json
{
  "status": "success",
  "data": { /* actual payload */ }
}
```
If you choose this, keep the examples above as `data`.

## Idempotency
- Support `Idempotency-Key` header for POST writes (create list, results, complete)

## Pagination & Filtering
- Word lists: `page`, `limit`, `search`, `favorite`, `sort`
- Words: Use `GET /word-lists/{id}?include=words&page=1&limit=100&search=...&favorite=true`
  - Response shape for words pagination (if implemented)
  ```json
  {
    "id": "wl_1",
    "name": "...",
    "description": "...",
    "wordCount": 120,
    "isFavorite": false,
    "createdAt": "...",
    "updatedAt": "...",
    "words": {
      "data": [ { "id": "w_1", "word": "...", "translation": "..." } ],
      "pagination": { "page": 1, "limit": 100, "total": 120 }
    }
  }
  ```

## Localization
- API returns data only. UI strings come from `locales/**/games.*`

## Telemetry & Audit
- Log session start/complete, per-word results, list/word mutations
- Metrics: session length, accuracy distribution, word difficulty cohorts

## Rate Limits (recommended)
- Start session: 30/min/user
- Record result: 120/min/user
- CRUD lists/words: 60/min/user

## Examples End-to-End

1) Load lists → pick one
- GET `/v1/word-lists`
- GET `/v1/word-lists/wl_1`

2) Start session
```http
POST /v1/flashcards/sessions
Authorization: Bearer <jwt>
Content-Type: application/json

{"wordListId":"wl_1"}
```
→ 201 `FlashcardSession`

3) Record results while practicing
```http
POST /v1/flashcards/sessions/fs_123/results
Authorization: Bearer <jwt>
Content-Type: application/json

{"wordId":"w_1","isCorrect":true,"timeSpent":900,"attempts":1}
```
→ 200 `{ "ok": true }`

4) Complete
```http
POST /v1/flashcards/sessions/fs_123/complete
Authorization: Bearer <jwt>
Content-Type: application/json

{"progress":{"current":20,"total":20,"correct":15,"incorrect":5}}
```
→ 200 `FlashcardSession` (with `completedAt`)

## Non-Functional Requirements
- Latency targets: GET < 300ms; POST < 800ms p95
- Strong validation; descriptive errors
- ISO-8601 UTC timestamps; UUID/ULID ids
- ETag on list/word GET for caching; conditional requests supported

## Frontend Mapping (from current mocks)
- `wordListsApi.getWordLists` → GET `/v1/word-lists`
- `wordListsApi.getWordList` → GET `/v1/word-lists/{id}`
- `wordListsApi.createWordList` → POST `/v1/word-lists`
- `wordListsApi.updateWordList` → PATCH `/v1/word-lists/{id}`
- `wordListsApi.deleteWordList` → DELETE `/v1/word-lists/{id}`
- `wordsApi.addWord` → POST `/v1/word-lists/{id}/words`
- `wordsApi.updateWord` → PATCH `/v1/word-lists/{id}/words/{wordId}`
- `wordsApi.deleteWord` → DELETE `/v1/word-lists/{id}/words/{wordId}`
- `wordsApi.toggleFavorite` → POST `/v1/word-lists/{id}/words/{wordId}/favorite`
- `flashcardApi.startSession` → POST `/v1/flashcards/sessions`
- `flashcardApi.recordPracticeResult` → POST `/v1/flashcards/sessions/{id}/results`
- `flashcardApi.completeSession` → POST `/v1/flashcards/sessions/{id}/complete`

## Open Configurations (to confirm)
- Max words returned per session (server cap)
- Whether server shuffles word order or preserves list order
- Whether to store only latest result per word per session or all attempts
- Accuracy rounding policy

---

This specification aligns with the Flashcards UI and existing client code and should be sufficient for backend engineers to implement services without further clarification.


