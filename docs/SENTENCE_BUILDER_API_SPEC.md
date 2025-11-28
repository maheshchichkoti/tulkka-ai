# Sentence Builder – Backend API Specification (TULKKA)

## Overview

This document defines backend APIs to support the Games → Sentence Builder feature and its nested flows (Topic / Lesson / Custom / Unknown practice modes, hints, mistakes practice, results). It is aligned with the current app code in `app/games/sentence-builder.tsx`.

Primary use cases:
- Browse available Topics and Lessons
- Start a Sentence Builder session (by topic, by lesson, custom mix, or from previous mistakes)
- For each item, show shuffled tokens and let the user assemble the sentence
- Provide contextual hints after wrong attempts
- Record per-item results including error type and attempts
- Complete a session and review summaries; optionally practice mistakes again

## Data Model

SentenceItem
```json
{
  "id": "sb_it_101",
  "english": "The CEO announced that the company would mitigate its impact.",
  "translation": "...", 
  "topic": "formal_register",           
  "lesson": "Formal Register 1",        
  "difficulty": "medium",               
  "tokens": ["The","CEO","announced","that","the","company","would","mitigate","its","impact","."],
  "accepted": [                          
    ["The","CEO","announced","that","the","company","would","mitigate","its","impact","."]
  ],
  "distractors": [],                     
  "metadata": { "source": "authoring" }
}
```

Notes:
- `tokens` are canonical tokens including punctuation tokens (recommended) so the client can shuffle/render reliably.
- `accepted` is a list of one or more acceptable token sequences (to allow minor variants).
- `distractors` (optional) extra tokens that may be mixed into the pool to increase difficulty.

Session & Result
```json
{
  "id": "sb_sess_9f3",
  "mode": "topic",                      
  "topicId": "formal_register",        
  "lessonId": null,                      
  "items": [/* SentenceItem summary (id + minimal fields) */],
  "progress": { "current": 0, "total": 10, "correct": 0, "incorrect": 0 },
  "startedAt": "2025-10-16T12:00:00Z",
  "completedAt": null
}
```

Result payload per item
```json
{
  "itemId": "sb_it_101",
  "userTokens": ["The","CEO","announced","that","the","company","would","mitigate","its","impact","."],
  "isCorrect": true,
  "attempts": 1,
  "timeSpent": 5200,
  "errorType": "word_order"              
}
```

Error types (from app logic): `word_order`, `missing_words`, `extra_words`.

## Security & Headers
- Authorization: `Bearer <jwt>` (all endpoints below)
- Content-Type: `application/json`
- Accept-Language: `<locale>` (optional)

## Error Shape
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "...",
    "details": {}
  }
}
```
Common codes: `UNAUTHORIZED`, `FORBIDDEN`, `VALIDATION_ERROR`, `RESOURCE_NOT_FOUND`, `CONFLICT`, `RATE_LIMITED`, `SERVER_ERROR`.

## Validation Rules
- `difficulty` ∈ `easy|medium|hard`
- `selectedItemIds` must belong to the user/filters requested
- `attempts` ≥ 1; `timeSpent` ≥ 0
- `userTokens` must not be empty and contain only known `tokens` + `distractors`

## Endpoints

### Catalog (Topics, Lessons, Items)

GET `/v1/sentence-builder/topics`
- Response 200
```json
{ "topics": [ { "id": "phrasal_verbs", "name": "Phrasal Verbs" }, { "id": "formal_register", "name": "Formal Register" } ] }
```

GET `/v1/sentence-builder/lessons`
- Query: `?topicId=formal_register`
- Response 200
```json
{ "lessons": [ { "id": "fr_1", "title": "Formal Register 1", "topicId": "formal_register", "items": 8 } ] }
```

GET `/v1/sentence-builder/items`
- Query: `?topicId=formal_register&lessonId=fr_1&difficulty=medium&page=1&limit=50`
- Response 200 (summaries by default)
```json
{
  "data": [
    { "id": "sb_it_101", "english": "The CEO announced ...", "topic": "formal_register", "lesson": "fr_1", "difficulty": "medium" }
  ],
  "pagination": { "page": 1, "limit": 50, "total": 28 }
}
```
- To fetch full items with tokens/accepted sets: `?include=tokens`
```json
{ "data": [ { "id": "sb_it_101", "tokens": ["The","CEO",...], "accepted": [["The","CEO",...]] } ], "pagination": {"page":1,"limit":50,"total":28} }
```

### Sessions

POST `/v1/sentence-builder/sessions`
- Purpose: Start a session for a given mode
- Body (one of the following)
```json
{ "mode": "topic", "topicId": "formal_register", "difficulty": "medium", "limit": 10 }
```
```json
{ "mode": "lesson", "lessonId": "fr_1", "difficulty": "medium" }
```
```json
{ "mode": "custom", "selectedItemIds": ["sb_it_101","sb_it_205"] }
```
```json
{ "mode": "mistakes" }
```
- Response 201
```json
{
  "id": "sb_sess_9f3",
  "mode": "topic",
  "topicId": "formal_register",
  "lessonId": null,
  "items": [ { "id": "sb_it_101" }, { "id": "sb_it_205" } ],
  "progress": { "current": 0, "total": 10, "correct": 0, "incorrect": 0 },
  "startedAt": "2025-10-16T12:00:00Z",
  "completedAt": null
}
```

GET `/v1/sentence-builder/sessions/{sessionId}`
- Response 200 → full session (may include `include=items` to expand token data)

POST `/v1/sentence-builder/sessions/{sessionId}/results`
- Purpose: Record per-item result
- Body
```json
{ "itemId":"sb_it_101", "userTokens":["The","CEO",...], "isCorrect":false, "attempts":2, "timeSpent":4300, "errorType":"word_order" }
```
- Response 200 `{ "ok": true }`
- Side effects
  - Update user-level mistake store for `mode: mistakes`
  - Increment per-item stats if tracked (attempts, success rate)
  - Update session `progress`

POST `/v1/sentence-builder/sessions/{sessionId}/complete`
- Body (optional summary)
```json
{ "progress": { "current": 10, "total": 10, "correct": 7, "incorrect": 3 } }
```
- Response 200 → session with `completedAt`
```json
{ "id":"sb_sess_9f3", "mode":"topic", "topicId":"formal_register", "lessonId":null, "items":[], "progress":{ "current":10, "total":10, "correct":7, "incorrect":3 }, "startedAt":"2025-10-16T12:00:00Z", "completedAt":"2025-10-16T12:25:00Z" }
```

### Hints & Content Helpers (optional)

GET `/v1/sentence-builder/items/{itemId}/hint`
- Purpose: Provide a context hint after multiple wrong attempts
- Response 200
```json
{ "itemId": "sb_it_101", "hint": "Focus on formal verbs like 'announce' and 'mitigate'." }
```

GET `/v1/sentence-builder/items/{itemId}/tts`
- Purpose: Pre-generated audio for listening practice (optional)
- Response 200
```json
{ "itemId": "sb_it_101", "audioUrl": "https://cdn.tulkka.com/sb/sb_it_101_en_us.mp3", "language": "en-US" }
```

### Mistakes Review

GET `/v1/sentence-builder/mistakes`
- Query: `?page=1&limit=50`
- Response 200
```json
{
  "data": [ { "itemId": "sb_it_205", "lastErrorType": "word_order", "lastAnsweredAt": "2025-10-15T10:00:00Z" } ],
  "pagination": { "page": 1, "limit": 50, "total": 8 }
}
```

## Idempotency
- Support `Idempotency-Key` for POST writes (create session, results, complete)

## Pagination & Filtering
- Catalog endpoints accept `page`, `limit`, `difficulty`, `topicId`, `lessonId`, `include=tokens`

## Rate Limits (recommended)
- Start session: 30/min/user
- Record result: 120/min/user
- Hints/tts: 120/min/user

## Telemetry & Audit
- Log session start/complete, per-item results, hint requests
- Metrics: accuracy by topic/lesson/difficulty, average attempts per item, time per item

## Frontend Mapping
- The app supports modes: `topic`, `lesson`, `custom`, `mistakes`. Map to:
  - `POST /v1/sentence-builder/sessions` (mode config)
  - `POST /v1/sentence-builder/sessions/{id}/results` per item
  - `POST /v1/sentence-builder/sessions/{id}/complete`
  - `GET /v1/sentence-builder/mistakes` when starting mistakes mode
  - Catalog endpoints to populate selection UIs

## Examples End-to-End

1) Start by topic
```http
POST /v1/sentence-builder/sessions
Authorization: Bearer <jwt>
Content-Type: application/json

{ "mode": "topic", "topicId": "formal_register", "difficulty": "medium", "limit": 10 }
```
→ 201 `Session`

2) Record result
```http
POST /v1/sentence-builder/sessions/sb_sess_9f3/results
Authorization: Bearer <jwt>
Content-Type: application/json

{ "itemId":"sb_it_101", "userTokens":["The","CEO",...], "isCorrect":true, "attempts":1, "timeSpent":5200, "errorType":"word_order" }
```
→ 200 `{ "ok": true }`

3) Complete
```http
POST /v1/sentence-builder/sessions/sb_sess_9f3/complete
Authorization: Bearer <jwt>
Content-Type: application/json

{ "progress": { "current": 10, "total": 10, "correct": 7, "incorrect": 3 } }
```
→ 200 `Session` with `completedAt`

## Open Configurations (to confirm)
- Whether server returns full tokens/accepted sets or client requests with `include=tokens`
- Whether to provide `distractors` automatically per difficulty
- Alternate acceptable tokenizations (e.g., punctuation spacing rules)
- Whether server normalizes capitalization for evaluation (client currently evaluates locally)

---

This specification is designed to be drop-in for the existing Sentence Builder UI and provides the necessary contracts for backend implementation.


