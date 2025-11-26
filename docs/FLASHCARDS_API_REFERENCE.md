# Flashcards API Reference for Frontend Developers

> **Base URL:** `https://api.tulkka.com` (or your deployed backend URL)  
> **Authentication:** Optional `X-User-Id` header for user identification  
> **Content-Type:** `application/json`

---

## Quick Start

```typescript
// Example: Create a word list and start practicing
const headers = {
  "Content-Type": "application/json",
  "X-User-Id": "user-123", // Your user ID
};

// 1. Create a word list
const list = await fetch("/v1/word-lists", {
  method: "POST",
  headers,
  body: JSON.stringify({ name: "My Vocabulary", description: "Daily words" }),
}).then((r) => r.json());

// 2. Add words
await fetch(`/v1/word-lists/${list.id}/words`, {
  method: "POST",
  headers,
  body: JSON.stringify({ word: "Hello", translation: "مرحبا" }),
});

// 3. Start a flashcard session
const session = await fetch("/v1/flashcards/sessions", {
  method: "POST",
  headers,
  body: JSON.stringify({ wordListId: list.id }),
}).then((r) => r.json());

// 4. Record results as user practices
await fetch(`/v1/flashcards/sessions/${session.id}/results`, {
  method: "POST",
  headers,
  body: JSON.stringify({
    wordId: session.words[0].id,
    isCorrect: true,
    timeSpentMs: 1200,
    attempts: 1,
  }),
});

// 5. Complete session
const completed = await fetch(
  `/v1/flashcards/sessions/${session.id}/complete`,
  {
    method: "POST",
    headers,
  }
).then((r) => r.json());
```

---

## API Endpoints

### 1. Word Lists

#### GET `/v1/word-lists`

List all word lists for the current user.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | number | 1 | Page number (1-indexed) |
| `limit` | number | 20 | Items per page (max 100) |
| `search` | string | - | Search by name |
| `favorite` | boolean | - | Filter by favorite status |
| `sort` | string | `createdAt` | Sort by: `name`, `createdAt`, `updatedAt` |

**Response 200:**

```json
{
  "data": [
    {
      "id": "wl_abc123",
      "name": "Basic Vocabulary",
      "description": "Common words",
      "wordCount": 25,
      "isFavorite": false,
      "createdAt": "2025-01-15T10:00:00Z",
      "updatedAt": "2025-01-15T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 5
  }
}
```

---

#### POST `/v1/word-lists`

Create a new word list.

**Request Body:**

```json
{
  "name": "Animals", // Required, 1-120 chars
  "description": "Animal names" // Optional
}
```

**Response 201:**

```json
{
  "id": "wl_xyz789",
  "name": "Animals",
  "description": "Animal names",
  "wordCount": 0,
  "isFavorite": false,
  "createdAt": "2025-01-15T10:00:00Z",
  "updatedAt": "2025-01-15T10:00:00Z"
}
```

---

#### GET `/v1/word-lists/{listId}`

Get a specific word list, optionally with its words.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `include` | string | Set to `words` to include words |
| `page` | number | Page for words (default 1) |
| `limit` | number | Words per page (default 100, max 200) |
| `search` | string | Search words |
| `favorite` | boolean | Filter favorite words |

**Response 200 (with `?include=words`):**

```json
{
  "id": "wl_abc123",
  "name": "Basic Vocabulary",
  "description": "Common words",
  "wordCount": 25,
  "isFavorite": false,
  "createdAt": "2025-01-15T10:00:00Z",
  "updatedAt": "2025-01-15T10:00:00Z",
  "words": {
    "data": [
      {
        "id": "w_123",
        "word": "Hello",
        "translation": "مرحبا",
        "notes": "Common greeting",
        "isFavorite": false,
        "practiceCount": 5,
        "correctCount": 4,
        "accuracy": 80,
        "lastPracticed": "2025-01-14T10:00:00Z",
        "createdAt": "2025-01-10T10:00:00Z",
        "updatedAt": "2025-01-14T10:00:00Z"
      }
    ],
    "pagination": { "page": 1, "limit": 100, "total": 25 }
  }
}
```

---

#### PATCH `/v1/word-lists/{listId}`

Update a word list (partial update).

**Request Body:**

```json
{
  "name": "Updated Name", // Optional
  "description": "New desc", // Optional
  "isFavorite": true // Optional
}
```

**Response 200:** Updated word list object

---

#### DELETE `/v1/word-lists/{listId}`

Delete a word list and all its words.

**Response 204:** No content

---

#### POST `/v1/word-lists/{listId}/favorite`

Toggle favorite status for a word list.

**Request Body:**

```json
{ "isFavorite": true }
```

**Response 200:**

```json
{ "ok": true }
```

---

### 2. Words

#### POST `/v1/word-lists/{listId}/words`

Add a word to a list.

**Request Body:**

```json
{
  "word": "Hello", // Required, 1-120 chars
  "translation": "مرحبا", // Required, 1-240 chars
  "notes": "Common greeting", // Optional
  "isFavorite": false // Optional, default false
}
```

**Response 201:**

```json
{
  "id": "w_abc123",
  "word": "Hello",
  "translation": "مرحبا",
  "notes": "Common greeting",
  "isFavorite": false,
  "practiceCount": 0,
  "correctCount": 0,
  "accuracy": 0,
  "lastPracticed": null,
  "createdAt": "2025-01-15T10:00:00Z",
  "updatedAt": "2025-01-15T10:00:00Z"
}
```

---

#### PATCH `/v1/word-lists/{listId}/words/{wordId}`

Update a word (partial update).

**Request Body:**

```json
{
  "word": "Hi", // Optional
  "translation": "أهلاً", // Optional
  "notes": "Informal", // Optional
  "isFavorite": true // Optional
}
```

**Response 200:** Updated word object

---

#### DELETE `/v1/word-lists/{listId}/words/{wordId}`

Delete a word from a list.

**Response 204:** No content

---

#### POST `/v1/word-lists/{listId}/words/{wordId}/favorite`

Toggle favorite status for a word.

**Request Body:**

```json
{ "isFavorite": true }
```

**Response 200:**

```json
{ "ok": true }
```

---

### 3. Flashcard Sessions

#### POST `/v1/flashcards/sessions`

Start a new flashcard practice session.

**Headers:**

- `Idempotency-Key` (optional): UUID for safe retries

**Request Body:**

```json
{
  "wordListId": "wl_abc123", // Required
  "selectedWordIds": ["w_1", "w_2"], // Optional - subset of words
  "shuffle": true // Optional - randomize order
}
```

**Response 201:**

```json
{
  "id": "fs_session123",
  "wordListId": "wl_abc123",
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
      "lastPracticed": "2025-01-14T10:00:00Z",
      "createdAt": "2025-01-10T10:00:00Z",
      "updatedAt": "2025-01-14T10:00:00Z"
    }
  ],
  "progress": {
    "current": 0,
    "total": 10,
    "correct": 0,
    "incorrect": 0
  },
  "startedAt": "2025-01-15T12:00:00Z",
  "completedAt": null
}
```

---

#### GET `/v1/flashcards/sessions/{sessionId}`

Get session state (for resuming).

**Response 200:** Same as POST response above

---

#### POST `/v1/flashcards/sessions/{sessionId}/results`

Record a practice result for a word.

**Headers:**

- `Idempotency-Key` (optional): UUID for safe retries

**Request Body:**

```json
{
  "wordId": "w_1", // Required
  "isCorrect": true, // Required
  "timeSpentMs": 1200, // Required, milliseconds spent
  "attempts": 1, // Required, number of attempts
  "clientResultId": "uuid" // Optional, for deduplication
}
```

**Response 200:**

```json
{
  "ok": true,
  "progress": {
    "current": 1,
    "total": 10,
    "correct": 1,
    "incorrect": 0
  },
  "word": {
    "id": "w_1",
    "practiceCount": 6,
    "correctCount": 5,
    "accuracy": 83,
    "lastPracticed": "2025-01-15T12:05:00Z"
  }
}
```

**Side Effects:**

- Updates word's `practiceCount`, `correctCount`, `accuracy`, `lastPracticed`
- Tracks mistakes for "needs practice" mode

---

#### POST `/v1/flashcards/sessions/{sessionId}/complete`

Complete a flashcard session.

**Request Body (optional):**

```json
{
  "progress": {
    "current": 10,
    "total": 10,
    "correct": 8,
    "incorrect": 2
  }
}
```

**Response 200:**

```json
{
  "id": "fs_session123",
  "wordListId": "wl_abc123",
  "words": [],
  "progress": {
    "current": 10,
    "total": 10,
    "correct": 8,
    "incorrect": 2
  },
  "masteredWordIds": ["w_1", "w_3", "w_5"],
  "needsPracticeWordIds": ["w_2", "w_4"],
  "startedAt": "2025-01-15T12:00:00Z",
  "completedAt": "2025-01-15T12:30:00Z"
}
```

---

### 4. Statistics

#### GET `/v1/flashcards/stats/me`

Get user's flashcard statistics.

**Response 200:**

```json
{
  "totalSessions": 32,
  "completedSessions": 28,
  "totalCorrect": 450,
  "totalIncorrect": 90,
  "accuracy": 83
}
```

---

## Error Handling

All errors follow this format:

```json
{
  "detail": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Word list not found",
    "details": { "resourceId": "wl_invalid" }
  }
}
```

**Common Error Codes:**
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `UNKNOWN_WORD` | 400 | Word ID not found |
| `WORD_LIST_NOT_FOUND` | 404 | Word list doesn't exist |
| `SESSION_NOT_FOUND` | 404 | Session doesn't exist |
| `SESSION_COMPLETED` | 409 | Session already completed |

---

## Frontend Service Mapping

```typescript
// services/api/flashcardService.ts

export const wordListsApi = {
  getWordLists: (params) => GET("/v1/word-lists", params),
  getWordList: (id, params) => GET(`/v1/word-lists/${id}`, params),
  createWordList: (data) => POST("/v1/word-lists", data),
  updateWordList: (id, data) => PATCH(`/v1/word-lists/${id}`, data),
  deleteWordList: (id) => DELETE(`/v1/word-lists/${id}`),
  toggleFavorite: (id, isFavorite) =>
    POST(`/v1/word-lists/${id}/favorite`, { isFavorite }),
};

export const wordsApi = {
  addWord: (listId, data) => POST(`/v1/word-lists/${listId}/words`, data),
  updateWord: (listId, wordId, data) =>
    PATCH(`/v1/word-lists/${listId}/words/${wordId}`, data),
  deleteWord: (listId, wordId) =>
    DELETE(`/v1/word-lists/${listId}/words/${wordId}`),
  toggleFavorite: (listId, wordId, isFavorite) =>
    POST(`/v1/word-lists/${listId}/words/${wordId}/favorite`, { isFavorite }),
};

export const flashcardApi = {
  startSession: (wordListId, options) =>
    POST("/v1/flashcards/sessions", { wordListId, ...options }),
  getSession: (sessionId) => GET(`/v1/flashcards/sessions/${sessionId}`),
  recordResult: (sessionId, result) =>
    POST(`/v1/flashcards/sessions/${sessionId}/results`, result),
  completeSession: (sessionId, progress) =>
    POST(`/v1/flashcards/sessions/${sessionId}/complete`, { progress }),
  getStats: () => GET("/v1/flashcards/stats/me"),
};
```

---

## TypeScript Types

```typescript
// types/flashcards.ts

interface WordList {
  id: string;
  name: string;
  description: string | null;
  wordCount: number;
  isFavorite: boolean;
  createdAt: string;
  updatedAt: string;
}

interface Word {
  id: string;
  word: string;
  translation: string;
  notes: string | null;
  isFavorite: boolean;
  practiceCount: number;
  correctCount: number;
  accuracy: number;
  lastPracticed: string | null;
  createdAt: string;
  updatedAt: string;
}

interface FlashcardSession {
  id: string;
  wordListId: string;
  words: Word[];
  progress: Progress;
  startedAt: string;
  completedAt: string | null;
}

interface Progress {
  current: number;
  total: number;
  correct: number;
  incorrect: number;
}

interface PracticeResult {
  wordId: string;
  isCorrect: boolean;
  timeSpentMs: number;
  attempts: number;
  clientResultId?: string;
}

interface FlashcardStats {
  totalSessions: number;
  completedSessions: number;
  totalCorrect: number;
  totalIncorrect: number;
  accuracy: number;
}

interface Pagination {
  page: number;
  limit: number;
  total: number;
}

interface PaginatedResponse<T> {
  data: T[];
  pagination: Pagination;
}
```

---

## Best Practices

### 1. Idempotency

Use `Idempotency-Key` header for POST requests to prevent duplicate operations:

```typescript
const headers = {
  "Idempotency-Key": crypto.randomUUID(),
  "Content-Type": "application/json",
};
```

### 2. Client Result ID

Use `clientResultId` when recording results to prevent duplicate submissions:

```typescript
await flashcardApi.recordResult(sessionId, {
  wordId: word.id,
  isCorrect: true,
  timeSpentMs: 1500,
  attempts: 1,
  clientResultId: `${sessionId}-${word.id}-${Date.now()}`,
});
```

### 3. Session Resume

Always check for existing session before starting a new one:

```typescript
try {
  const session = await flashcardApi.getSession(savedSessionId);
  if (!session.completedAt) {
    // Resume existing session
    return session;
  }
} catch (e) {
  // Session not found, start new one
}
```

### 4. Offline Support

Store results locally and sync when online:

```typescript
const pendingResults = [];

async function recordResult(result) {
  pendingResults.push(result);
  try {
    await flashcardApi.recordResult(sessionId, result);
    pendingResults.shift();
  } catch (e) {
    // Will retry later
  }
}
```

---

## Rate Limits

| Operation       | Limit        |
| --------------- | ------------ |
| Start session   | 30/min/user  |
| Record result   | 120/min/user |
| CRUD operations | 60/min/user  |

---

## Changelog

- **v1.0.0** (2025-01-15): Initial release with full Flashcards API
