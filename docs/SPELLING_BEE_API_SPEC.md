# Spelling Bee – Backend API Specification (TULKKA)

## Overview

This document defines all backend APIs required to power the Games → Spelling Bee experience in the mobile app.
It is based on the current UI and code in:
- `app/games/spelling-bee.tsx`
- Shared mocks & types: `services/api/flashcardService.ts` (Word, WordList)

Primary use cases:
- Users select a word list to practice
- App reads words aloud (client-side TTS) and the user types the spelling
- App records per-word attempts, correctness, and time
- Session completion returns summary and supports practicing incorrect words again

Notes
- Audio is currently handled on-device via Expo Speech; however, an optional pronunciation endpoint is defined for pre-generated audio.

## Definitions
- "Word": vocabulary entry with `word`, `translation`, optional `notes`
- "Word List": user-owned collection of words
- "Spelling Session": practice flow over words; the app checks correctness locally and reports results

## High-level Flows
1) Load Word Lists → select a list
2) Start Spelling Session → backend returns session with ordered words
3) For each word → post result `{userAnswer, isCorrect, attempts, timeSpent}`
4) Complete session → backend persists summary and returns final session payload

## Data Models

Word (same as Flashcards)
```json
{
  "id": "w_123",
  "word": "beautiful",
  "translation": "جميل",
  "notes": "", 
  "isFavorite": false,
  "practiceCount": 10,
  "correctCount": 7,
  "accuracy": 70,
  "lastPracticed": "2025-10-15T12:00:00Z",
  "createdAt": "2025-10-01T12:00:00Z",
  "updatedAt": "2025-10-15T12:00:00Z"
}
```

WordList (same as Flashcards)
```json
{
  "id": "wl_1",
  "name": "Animals",
  "description": "Common animal names",
  "wordCount": 20,
  "isFavorite": false,
  "createdAt": "2025-10-01T12:00:00Z",
  "updatedAt": "2025-10-15T12:00:00Z"
}
```

SpellingSession
```json
{
  "id": "sb_123",
  "wordListId": "wl_1",
  "words": [ /* array<Word> returned in practice order */ ],
  "progress": { "current": 0, "total": 20, "correct": 0, "incorrect": 0 },
  "startedAt": "2025-10-16T12:00:00Z",
  "completedAt": null
}
```

SpellingResult
```json
{
  "wordId": "w_123",
  "userAnswer": "beautifull",
  "isCorrect": false,
  "attempts": 2,
  "timeSpent": 2400
}
```

## Security & Headers
- Authorization: `Bearer <jwt>` for all endpoints
- Content-Type: `application/json`
- Accept-Language: `<locale>` (optional)

## Error Shape
```json
{
  "error": { "code": "VALIDATION_ERROR", "message": "...", "details": { } }
}
```
Common codes: UNAUTHORIZED, FORBIDDEN, VALIDATION_ERROR, RESOURCE_NOT_FOUND, CONFLICT, RATE_LIMITED, SERVER_ERROR

## Validation Rules
- `selectedWordIds` (if provided) must belong to the given list
- `attempts` ≥ 1; `timeSpent` ≥ 0
- `userAnswer` non-empty string (can be "[skipped]")

## Endpoints

### 1) Word Lists (shared with Flashcards)

GET `/v1/word-lists`
- Query: `?page=1&limit=20&search=...&favorite=true&sort=name|createdAt|updatedAt`
- Response 200
```json
{ "data": [ {"id":"wl_1","name":"Animals","wordCount":20,"isFavorite":false,"createdAt":"...","updatedAt":"..."} ],
  "pagination": {"page":1,"limit":20,"total":2} }
```
- Errors: 401, 429, 500

GET `/v1/word-lists/{listId}`
- Optional query: `?include=words&page=1&limit=200`
- Response 200 → WordList (optionally with words)
- Errors: 401, 403, 404, 500

### 2) Spelling Sessions

POST `/v1/spelling/sessions`
- Purpose: Start a spelling session
- Body
```json
{ "wordListId": "wl_1", "selectedWordIds": ["w_1","w_2"], "shuffle": true }
```
- Behavior: If `selectedWordIds` omitted → use all list words; if `shuffle` true → server may randomize order
- Response 201
```json
{
  "id": "sb_123",
  "wordListId": "wl_1",
  "words": [ { "id":"w_1","word":"elephant","translation":"فيل","isFavorite":false,"practiceCount":3,"correctCount":1,"accuracy":33,"createdAt":"...","updatedAt":"..." } ],
  "progress": { "current": 0, "total": 10, "correct": 0, "incorrect": 0 },
  "startedAt": "2025-10-16T12:00:00Z",
  "completedAt": null
}
```
- Errors: 400 (`not_in_list`), 401, 403, 404 (`unknown_list`), 429, 500

GET `/v1/spelling/sessions/{sessionId}`
- Response 200 → SpellingSession
- Errors: 401, 403, 404, 500

POST `/v1/spelling/sessions/{sessionId}/results`
- Purpose: Record a result for the current word
- Body
```json
{ "wordId":"w_1", "userAnswer":"elefant", "isCorrect":false, "attempts":2, "timeSpent":1800 }
```
- Response 200
```json
{ "ok": true }
```
- Side effects:
  - Update per-word counters (`practiceCount`, `correctCount`, `accuracy`, `lastPracticed`)
  - Update session `progress` (current, correct/incorrect)
- Errors: 400 (`unknown_word`, `not_in_list`, `validation_error`), 401, 403, 404 (unknown session), 409, 429, 500

POST `/v1/spelling/sessions/{sessionId}/complete`
- Body (optional summary from client)
```json
{ "progress": { "current": 10, "total": 10, "correct": 7, "incorrect": 3 } }
```
- Response 200
```json
{
  "id": "sb_123",
  "wordListId": "wl_1",
  "words": [],
  "progress": { "current": 10, "total": 10, "correct": 7, "incorrect": 3 },
  "startedAt": "2025-10-16T12:00:00Z",
  "completedAt": "2025-10-16T12:20:00Z"
}
```
- Errors: 400, 401, 403, 404, 409, 500

### 3) Optional Pronunciation Audio

GET `/v1/spelling/pronunciations/{wordId}`
- Purpose: Provide a pre-generated audio URL for a word if the app chooses to use server audio instead of device TTS
- Response 200
```json
{ "wordId": "w_1", "audioUrl": "https://cdn.tulkka.com/audio/w_1_en_us.mp3", "language": "en-US" }
```
- Errors: 401, 403, 404

## Idempotency
- Support `Idempotency-Key` on `POST /spelling/sessions`, `/results`, `/complete` for safe retries

## Pagination & Filtering
- Lists: `page`, `limit`, `search`, `favorite`, `sort`
- Words (optional pagination within list): return `words.data` + `words.pagination` as in Flashcards

## Rate Limits (recommended)
- Start session: 30/min/user
- Record result: 120/min/user
- Pronunciation fetch: 120/min/user

## Telemetry & Audit
- Log session start/complete and per-word results
- Metrics: attempts-to-correct histogram, accuracy by word length, session durations

## Frontend Mapping
- The screen currently uses `wordListsApi.getWordLists()` and performs local checking. To integrate server:
  - `GET /v1/word-lists` (load lists)
  - `POST /v1/spelling/sessions` (start)
  - `POST /v1/spelling/sessions/{id}/results` (each check)
  - `POST /v1/spelling/sessions/{id}/complete` (finish)
  - Optional: `GET /v1/spelling/pronunciations/{wordId}` for audio

## Examples End-to-End

1) Start a new session
```http
POST /v1/spelling/sessions
Authorization: Bearer <jwt>
Content-Type: application/json

{ "wordListId": "wl_1", "shuffle": true }
```
→ 201 `SpellingSession`

2) Report a result
```http
POST /v1/spelling/sessions/sb_123/results
Authorization: Bearer <jwt>
Content-Type: application/json

{ "wordId":"w_1", "userAnswer":"elefant", "isCorrect":false, "attempts":2, "timeSpent":1800 }
```
→ 200 `{ "ok": true }`

3) Complete session
```http
POST /v1/spelling/sessions/sb_123/complete
Authorization: Bearer <jwt>
Content-Type: application/json

{ "progress": { "current": 10, "total": 10, "correct": 7, "incorrect": 3 } }
```
→ 200 `SpellingSession` (with `completedAt`)

## Open Configurations (to confirm)
- Maximum words per session (server cap)
- Whether to limit maximum attempts per word tracked
- Whether server should randomize order (`shuffle`) or respect list order
- Whether to store all attempts or only final per word

---

This specification aligns with the Spelling Bee UI and should be sufficient for backend engineers to implement services without further clarification.


