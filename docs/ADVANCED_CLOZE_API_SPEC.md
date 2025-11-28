# Advanced Cloze – Backend API Specification (TULKKA)

## Overview

This document specifies backend APIs for the Games → Advanced Cloze experience and its nested flows (Topic/Lesson/Custom/Mistakes modes, hints, results, review). It aligns with `app/games/advanced-cloze.tsx`.

Primary use cases:
- Browse available topics and lessons for cloze exercises
- Start a cloze session with multiple-choice fill-in-the-blank questions
- Provide contextual hints after wrong attempts
- Record per-item results including selected answers and attempts
- Complete a session and review summaries with mistake analysis
- Practice mistakes again for targeted improvement

## Data Models

ClozeItem
```json
{
  "id": "ac_101",
  "topic": "phrasalVerbs",                   
  "lesson": "Business Phrasal Verbs",        
  "difficulty": "medium",                    
  "textParts": ["We need to ", " the old policy and ", " a new one."],
  "options": [
    ["phase out", "fade out", "face out"],
    ["bring up", "set up", "bring in"]
  ],
  "correct": ["phase out", "bring in"],
  "explanation": "\"Phase out\" means gradually stop using; \"bring in\" means introduce.",
  "metadata": { "source": "authoring" }
}
```

Topics: `phrasalVerbs`, `idioms`, `register`, `collocations`, `academic`
Difficulty: `easy|medium|hard`

ClozeSession
```json
{
  "id": "ac_sess_9f3",
  "mode": "topic",                     
  "topicId": "phrasalVerbs",           
  "lessonId": null,                     
  "items": [ { "id": "ac_101" } ],
  "progress": { "current": 0, "total": 10, "correct": 0, "incorrect": 0 },
  "startedAt": "2025-10-16T12:00:00Z",
  "completedAt": null
}
```

ClozeResult
```json
{
  "itemId": "ac_101",
  "selectedAnswers": ["phase out", "bring in"],
  "isCorrect": true,
  "attempts": 1,
  "timeSpent": 3200
}
```

ClozeMistake
```json
{
  "itemId": "ac_101",
  "item": { /* ClozeItem */ },
  "selectedAnswers": ["fade out", "set up"],
  "timestamp": 1697462400000
}
```

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
- `selectedItemIds` must belong to requested filters
- `attempts` ≥ 1; `timeSpent` ≥ 0
- `selectedAnswers` array length must match number of blanks in item
- All selected answers must be valid options for their respective blanks

## Endpoints

### Catalog

GET `/v1/advanced-cloze/topics`
- Response 200
```json
{
  "topics": [
    { "id": "phrasalVerbs", "name": "Phrasal Verbs", "icon": "🔗", "description": "Multi-word verbs with particles" },
    { "id": "idioms", "name": "Idioms", "icon": "🎭", "description": "Fixed expressions with figurative meaning" },
    { "id": "register", "name": "Register", "icon": "🎯", "description": "Formal vs informal language" },
    { "id": "collocations", "name": "Collocations", "icon": "🤝", "description": "Words that commonly go together" },
    { "id": "academic", "name": "Academic", "icon": "🎓", "description": "Academic writing conventions" }
  ]
}
```

GET `/v1/advanced-cloze/lessons`
- Query: `?topicId=phrasalVerbs`
- Response 200
```json
{
  "lessons": [
    { "id": "pv_business", "title": "Business Phrasal Verbs", "topicId": "phrasalVerbs", "items": 8 },
    { "id": "pv_communication", "title": "Communication Phrasal Verbs", "topicId": "phrasalVerbs", "items": 6 }
  ]
}
```

GET `/v1/advanced-cloze/items`
- Query: `?topicId=phrasalVerbs&lessonId=pv_business&difficulty=medium&page=1&limit=50`
- Response 200 (summaries by default)
```json
{
  "data": [
    { "id": "ac_101", "topic": "phrasalVerbs", "lesson": "pv_business", "difficulty": "medium", "textParts": ["We need to ", " the old policy and ", " a new one."] }
  ],
  "pagination": { "page": 1, "limit": 50, "total": 28 }
}
```
- To request full items with options/explanations: `?include=options,explanation`
```json
{
  "data": [
    { "id": "ac_101", "options": [["phase out", "fade out", "face out"], ["bring up", "set up", "bring in"]], "correct": ["phase out", "bring in"], "explanation": "..." }
  ],
  "pagination": { "page": 1, "limit": 50, "total": 28 }
}
```

### Sessions

POST `/v1/advanced-cloze/sessions`
- Purpose: Start a cloze session
- Body (one of)
```json
{ "mode": "topic", "topicId": "phrasalVerbs", "difficulty": "medium", "limit": 10 }
```
```json
{ "mode": "lesson", "lessonId": "pv_business", "difficulty": "medium" }
```
```json
{ "mode": "custom", "selectedItemIds": ["ac_101", "ac_205"] }
```
```json
{ "mode": "mistakes" }
```
- Response 201
```json
{
  "id": "ac_sess_9f3",
  "mode": "topic",
  "topicId": "phrasalVerbs",
  "lessonId": null,
  "items": [ { "id": "ac_101" }, { "id": "ac_205" } ],
  "progress": { "current": 0, "total": 10, "correct": 0, "incorrect": 0 },
  "startedAt": "2025-10-16T12:00:00Z",
  "completedAt": null
}
```

GET `/v1/advanced-cloze/sessions/{sessionId}`
- Response 200 → ClozeSession (optionally expand items with `include=options`)

POST `/v1/advanced-cloze/sessions/{sessionId}/results`
- Purpose: Record result per item
- Body
```json
{ "itemId": "ac_101", "selectedAnswers": ["phase out", "bring in"], "isCorrect": true, "attempts": 1, "timeSpent": 3200 }
```
- Response 200 `{ "ok": true }`
- Side effects
  - Update session progress (current, correct/incorrect)
  - Store mistakes for future `mode: mistakes`

POST `/v1/advanced-cloze/sessions/{sessionId}/complete`
- Body (optional summary)
```json
{ "progress": { "current": 10, "total": 10, "correct": 7, "incorrect": 3 } }
```
- Response 200
```json
{ "id": "ac_sess_9f3", "mode": "topic", "topicId": "phrasalVerbs", "lessonId": null, "items": [], "progress": { "current": 10, "total": 10, "correct": 7, "incorrect": 3 }, "startedAt": "2025-10-16T12:00:00Z", "completedAt": "2025-10-16T12:18:00Z" }
```

### Hints

GET `/v1/advanced-cloze/items/{itemId}/hint`
- Purpose: Provide topic-specific hint after wrong attempts
- Response 200
```json
{ "itemId": "ac_101", "hint": "Business phrasal verbs often involve 'phase out' (gradual removal) and 'bring in' (introduction)." }
```

### Mistakes Review

GET `/v1/advanced-cloze/mistakes`
- Query: `?page=1&limit=50`
- Response 200
```json
{
  "data": [
    { "itemId": "ac_101", "topic": "phrasalVerbs", "selectedAnswers": ["fade out", "set up"], "lastAnsweredAt": "2025-10-15T10:00:00Z" }
  ],
  "pagination": { "page": 1, "limit": 50, "total": 6 }
}
```

### Analytics (optional)

GET `/v1/advanced-cloze/analytics/topic-performance`
- Query: `?topicId=phrasalVerbs&timeframe=30d`
- Response 200
```json
{
  "topicId": "phrasalVerbs",
  "accuracy": 78,
  "totalAttempts": 45,
  "commonMistakes": [
    { "itemId": "ac_101", "mistakeCount": 8, "commonWrongAnswer": "fade out" }
  ],
  "improvement": { "trend": "up", "percentage": 12 }
}
```

## Idempotency
- Support `Idempotency-Key` header for POST writes (start, results, complete)

## Pagination & Filtering
- Catalog supports `page`, `limit`, `difficulty`, `topicId`, `lessonId`, `include`

## Rate Limits (recommended)
- Start session: 30/min/user
- Record result: 120/min/user
- Hints: 120/min/user

## Telemetry & Audit
- Log session start/complete; per-item results; hint requests
- Metrics: accuracy by topic/lesson/difficulty; common wrong answers; time per item

## Frontend Mapping
- Modes supported in UI: `topic`, `lesson`, `custom`, `mistakes`
  - Map to `POST /v1/advanced-cloze/sessions` with appropriate body
  - Per-item result: `POST /v1/advanced-cloze/sessions/{id}/results`
  - Complete: `POST /v1/advanced-cloze/sessions/{id}/complete`
  - Mistakes view: `GET /v1/advanced-cloze/mistakes`
  - Hints by item: `GET /v1/advanced-cloze/items/{id}/hint`
  - Catalog: `GET /v1/advanced-cloze/topics`, `/lessons`, `/items`

## End-to-End Examples

1) Start by topic
```http
POST /v1/advanced-cloze/sessions
Authorization: Bearer <jwt>
Content-Type: application/json

{ "mode": "topic", "topicId": "phrasalVerbs", "difficulty": "medium", "limit": 10 }
```
→ 201 `ClozeSession`

2) Record a result
```http
POST /v1/advanced-cloze/sessions/ac_sess_9f3/results
Authorization: Bearer <jwt>
Content-Type: application/json

{ "itemId": "ac_101", "selectedAnswers": ["phase out", "bring in"], "isCorrect": true, "attempts": 1, "timeSpent": 3200 }
```
→ 200 `{ "ok": true }`

3) Get hint
```http
GET /v1/advanced-cloze/items/ac_101/hint
Authorization: Bearer <jwt>
```
→ 200 `{ "itemId": "ac_101", "hint": "..." }`

4) Complete
```http
POST /v1/advanced-cloze/sessions/ac_sess_9f3/complete
Authorization: Bearer <jwt>
Content-Type: application/json

{ "progress": { "current": 10, "total": 10, "correct": 7, "incorrect": 3 } }
```
→ 200 `ClozeSession` with `completedAt`

## Open Configurations (to confirm)
- Whether to return full items at session start or let client fetch with `include` per item
- Server-side rule for showing hints (after N wrong attempts) or client-driven
- Randomization/shuffling policy per session
- Whether to track partial credit for partially correct answers

---

This specification mirrors the Advanced Cloze UX and provides all contracts needed for backend implementation.
