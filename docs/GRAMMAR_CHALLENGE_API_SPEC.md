# Grammar Challenge – Backend API Specification (TULKKA)

## Overview

This document specifies the backend APIs for the Games → Grammar Challenge experience and nested flows (Topic/Lesson/Custom/Mistakes modes, hints, results, review). It aligns with `app/games/grammar-challenge.tsx`.

Primary use cases:
- Browse categories (topics) and lessons
- Start a challenge session using filtered question sets
- For each question, choose among multiple-choice options
- Provide targeted hints after 2 wrong attempts
- Record per-question results (selected answer, attempts, time)
- Complete a session and review summaries, with “practice mistakes” mode

## Data Models

GrammarQuestion
```json
{
  "id": "gc_q_101",
  "category": "tense",                      
  "difficulty": "medium",                   
  "lesson": "Past Perfect vs Simple Past",  
  "prompt": "By the time we arrived, the film ____.",
  "options": ["has started","had started","was starting","has been starting"],
  "correctIndex": 1,
  "explanation": "Past perfect shows an action completed before another past action.",
  "metadata": { "source": "authoring" }
}
```

GrammarSession
```json
{
  "id": "gc_sess_9f3",
  "mode": "topic",                     
  "categoryId": "tense",               
  "lessonId": null,                     
  "questions": [ { "id": "gc_q_101" } ],
  "progress": { "current": 0, "total": 10, "correct": 0, "incorrect": 0 },
  "startedAt": "2025-10-16T12:00:00Z",
  "completedAt": null
}
```

GrammarResult
```json
{
  "questionId": "gc_q_101",
  "selectedAnswer": 0,
  "isCorrect": false,
  "attempts": 2,
  "timeSpent": 1800
}
```

Categories (from UI): `tense`, `agreement`, `modifier`, `preposition`, `article`, `conditional`, `collocation`, `parallelism`, `punctuation`, `wordChoice`.
Difficulty: `easy|medium|hard`.

## Security & Headers
- Authorization: `Bearer <jwt>`
- Content-Type: `application/json`
- Accept-Language: `<locale>` (optional)

## Error Shape
```json
{
  "error": { "code": "VALIDATION_ERROR", "message": "...", "details": {} }
}
```
Common: `UNAUTHORIZED`, `FORBIDDEN`, `VALIDATION_ERROR`, `RESOURCE_NOT_FOUND`, `CONFLICT`, `RATE_LIMITED`, `SERVER_ERROR`.

## Validation Rules
- `selectedQuestionIds` must belong to the requested filters
- `attempts` ≥ 1; `timeSpent` ≥ 0; `selectedAnswer` in range of `options`

## Endpoints

### Catalog

GET `/v1/grammar-challenge/categories`
- Response 200
```json
{ "categories": [ { "id": "tense", "name": "Tenses" }, { "id": "agreement", "name": "Agreement" } ] }
```

GET `/v1/grammar-challenge/lessons`
- Query: `?categoryId=tense`
- Response 200
```json
{ "lessons": [ { "id": "tense_pp_sp", "title": "Past Perfect vs Simple Past", "categoryId": "tense", "questions": 8 } ] }
```

GET `/v1/grammar-challenge/questions`
- Query: `?categoryId=tense&lessonId=tense_pp_sp&difficulty=medium&page=1&limit=50`
- Response 200 (summaries by default)
```json
{
  "data": [
    { "id": "gc_q_101", "prompt": "By the time we arrived, the film ____.", "category": "tense", "lesson": "tense_pp_sp", "difficulty": "medium" }
  ],
  "pagination": { "page": 1, "limit": 50, "total": 28 }
}
```
- To request full questions (options/explanations) include `?include=options,explanation`
```json
{ "data": [ { "id": "gc_q_101", "options": ["has started","had started","was starting","has been starting"], "correctIndex": 1, "explanation": "..." } ], "pagination": {"page":1,"limit":50,"total":28} }
```

### Sessions

POST `/v1/grammar-challenge/sessions`
- Purpose: Start a session
- Body (one of)
```json
{ "mode": "topic", "categoryId": "tense", "difficulty": "medium", "limit": 10 }
```
```json
{ "mode": "lesson", "lessonId": "tense_pp_sp", "difficulty": "medium" }
```
```json
{ "mode": "custom", "selectedQuestionIds": ["gc_q_101","gc_q_205"] }
```
```json
{ "mode": "mistakes" }
```
- Response 201
```json
{
  "id": "gc_sess_9f3",
  "mode": "topic",
  "categoryId": "tense",
  "lessonId": null,
  "questions": [ { "id": "gc_q_101" }, { "id": "gc_q_205" } ],
  "progress": { "current": 0, "total": 10, "correct": 0, "incorrect": 0 },
  "startedAt": "2025-10-16T12:00:00Z",
  "completedAt": null
}
```

GET `/v1/grammar-challenge/sessions/{sessionId}`
- Response 200 → GrammarSession (optionally expand questions with `include=options`)

POST `/v1/grammar-challenge/sessions/{sessionId}/results`
- Purpose: Record result per question
- Body
```json
{ "questionId":"gc_q_101", "selectedAnswer": 0, "isCorrect": false, "attempts": 2, "timeSpent": 1700 }
```
- Response 200 `{ "ok": true }`
- Side effects
  - Update session progress (current, correct/incorrect)
  - Store mistakes for future `mode: mistakes`

POST `/v1/grammar-challenge/sessions/{sessionId}/skip`
- Purpose: User skipped a question (counts toward attempts/progress)
- Body
```json
{ "questionId": "gc_q_205" }
```
- Response 200 `{ "ok": true }`

POST `/v1/grammar-challenge/sessions/{sessionId}/complete`
- Body (optional summary)
```json
{ "progress": { "current": 10, "total": 10, "correct": 7, "incorrect": 3 } }
```
- Response 200
```json
{ "id":"gc_sess_9f3", "mode":"topic", "categoryId":"tense", "lessonId":null, "questions":[], "progress":{ "current":10, "total":10, "correct":7, "incorrect":3 }, "startedAt":"2025-10-16T12:00:00Z", "completedAt":"2025-10-16T12:18:00Z" }
```

### Hints

GET `/v1/grammar-challenge/questions/{questionId}/hint`
- Purpose: After ≥2 wrong attempts, return a category-targeted hint
- Response 200
```json
{ "questionId": "gc_q_101", "hint": "'By the time' usually pairs with Past Perfect to show prior completion." }
```

### Mistakes Review

GET `/v1/grammar-challenge/mistakes`
- Query: `?page=1&limit=50`
- Response 200
```json
{
  "data": [ { "questionId": "gc_q_101", "category": "tense", "lastSelected": 0, "lastAnsweredAt": "2025-10-15T10:00:00Z" } ],
  "pagination": { "page": 1, "limit": 50, "total": 6 }
}
```

## Idempotency
- Support `Idempotency-Key` header for POST writes (start, results, skip, complete)

## Pagination & Filtering
- Catalog supports `page`, `limit`, `difficulty`, `categoryId`, `lessonId`, `include`

## Rate Limits (recommended)
- Start session: 30/min/user
- Results/skip: 180/min/user
- Hints: 120/min/user

## Telemetry & Audit
- Log session start/complete; per-question results; hint requests
- Metrics: accuracy by category/lesson/difficulty; wrong-attempts distribution; time per question

## Frontend Mapping
- Modes supported in UI: `topic`, `lesson`, `custom`, `mistakes`
  - Map to `POST /v1/grammar-challenge/sessions` with appropriate body
  - Per-answer: `POST /v1/grammar-challenge/sessions/{id}/results`
  - Skip: `POST /v1/grammar-challenge/sessions/{id}/skip`
  - Complete: `POST /v1/grammar-challenge/sessions/{id}/complete`
  - Mistakes view: `GET /v1/grammar-challenge/mistakes`
  - Hints by question: `GET /v1/grammar-challenge/questions/{id}/hint`

## End-to-End Examples

1) Start by lesson
```http
POST /v1/grammar-challenge/sessions
Authorization: Bearer <jwt>
Content-Type: application/json

{ "mode": "lesson", "lessonId": "tense_pp_sp", "difficulty": "medium" }
```
→ 201 `GrammarSession`

2) Record an incorrect result
```http
POST /v1/grammar-challenge/sessions/gc_sess_9f3/results
Authorization: Bearer <jwt>
Content-Type: application/json

{ "questionId":"gc_q_101", "selectedAnswer": 0, "isCorrect": false, "attempts": 2, "timeSpent": 1700 }
```
→ 200 `{ "ok": true }`

3) Get hint
```http
GET /v1/grammar-challenge/questions/gc_q_101/hint
Authorization: Bearer <jwt>
```
→ 200 `{ "questionId": "gc_q_101", "hint": "..." }`

4) Complete
```http
POST /v1/grammar-challenge/sessions/gc_sess_9f3/complete
Authorization: Bearer <jwt>
Content-Type: application/json

{ "progress": { "current": 10, "total": 10, "correct": 7, "incorrect": 3 } }
```
→ 200 `GrammarSession` with `completedAt`

## Open Configurations (to confirm)
- Whether to return full questions at session start or let client fetch with `include` per question
- Server-side rule for showing hints (after N wrong attempts) or client-driven
- Randomization/shuffling policy per session
- Whether to track partial credit or only final correctness

---

This specification mirrors the Grammar Challenge UX and provides all contracts needed for backend implementation.


