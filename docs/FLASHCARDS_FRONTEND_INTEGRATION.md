# Flashcards & Word Lists – Frontend Integration Guide

> **Version:** 1.0.0  
> **Last Updated:** November 28, 2025  
> **Backend Status:** ✅ Production Ready

This document provides everything a frontend engineer needs to integrate the Flashcards and Word Lists APIs into the TULKKA mobile app.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [Base URL & Headers](#base-url--headers)
4. [Data Models](#data-models)
5. [Word Lists API](#word-lists-api)
6. [Words API](#words-api)
7. [Flashcard Sessions API](#flashcard-sessions-api)
8. [Catalog APIs (Topics & Lessons)](#catalog-apis-topics--lessons)
9. [Stats & Mistakes APIs](#stats--mistakes-apis)
10. [Error Handling](#error-handling)
11. [Complete UI Flow Examples](#complete-ui-flow-examples)
12. [Frontend Service Implementation](#frontend-service-implementation)
13. [Best Practices](#best-practices)

---

## Quick Start

### Minimal Flow: Practice a Word List

```typescript
// 1. Get user's word lists
const lists = await fetch("/v1/word-lists", { headers });
// → { data: [{ id, name, wordCount, ... }], pagination: {...} }

// 2. Start a flashcard session
const session = await fetch("/v1/flashcards/sessions", {
  method: "POST",
  headers,
  body: JSON.stringify({ mode: "custom", wordListId: "wl_123" }),
});
// → { id, words: [...], progress: { current: 0, total: 10, ... } }

// 3. For each card, record result
await fetch(`/v1/flashcards/sessions/${sessionId}/results`, {
  method: "POST",
  headers,
  body: JSON.stringify({
    wordId: "w_1",
    isCorrect: true,
    timeSpentMs: 1200,
    attempts: 1,
  }),
});
// → { ok: true, progress: { current: 1, total: 10, correct: 1, incorrect: 0 } }

// 4. Complete session
await fetch(`/v1/flashcards/sessions/${sessionId}/complete`, {
  method: "POST",
  headers,
});
// → { id, progress, completedAt, masteredWordIds, needsPracticeWordIds }
```

---

## Authentication

### Header: `X-User-Id`

All endpoints require the `X-User-Id` header to identify the current user.

| Header      | Type     | Required | Description                                       |
| ----------- | -------- | -------- | ------------------------------------------------- |
| `X-User-Id` | `string` | **Yes**  | The authenticated user's ID from your auth system |

**Important Notes:**

- The Games API **does NOT validate this ID** against a users table
- Pass the **same user ID** your main auth system uses (e.g., Firebase UID, Supabase user ID)
- If omitted, all data is stored under a shared `"anonymous-user"` profile
- In production, extract this from your JWT/session and pass it in every request

**Example:**

```typescript
const headers = {
  "Content-Type": "application/json",
  "X-User-Id": currentUser.id, // e.g., 'usr_abc123' from your auth
};
```

---

## Base URL & Headers

### Base URL

```
https://your-api-domain.com/v1
```

### Required Headers

| Header            | Value              | Required                                   |
| ----------------- | ------------------ | ------------------------------------------ |
| `Content-Type`    | `application/json` | For POST/PATCH requests                    |
| `X-User-Id`       | User's ID          | **Always**                                 |
| `Idempotency-Key` | UUID               | Recommended for POST (prevents duplicates) |

### Example Request

```typescript
const response = await fetch("https://api.tulkka.com/v1/word-lists", {
  method: "GET",
  headers: {
    "Content-Type": "application/json",
    "X-User-Id": "user-12345",
  },
});
```

---

## Data Models

### WordList

```typescript
interface WordList {
  id: string; // UUID, e.g., "wl_abc123"
  name: string; // 1-120 chars
  description: string | null;
  wordCount: number; // Auto-maintained by backend
  isFavorite: boolean;
  createdAt: string; // ISO 8601, e.g., "2025-01-15T10:30:00Z"
  updatedAt: string;

  // Only included when ?include=words
  words?: {
    data: Word[];
    pagination: Pagination;
  };
}
```

### Word

```typescript
interface Word {
  id: string; // UUID
  word: string; // 1-120 chars, the vocabulary term
  translation: string; // 1-240 chars
  notes: string | null; // Optional notes/context
  isFavorite: boolean;

  // Practice statistics (updated automatically)
  practiceCount: number; // Total times practiced
  correctCount: number; // Times answered correctly
  accuracy: number; // 0-100, auto-calculated
  lastPracticed: string | null; // ISO 8601 or null

  createdAt: string;
  updatedAt: string;
}
```

### FlashcardSession

```typescript
interface FlashcardSession {
  id: string; // Session UUID
  mode: "custom" | "lesson" | "topic" | "mistakes";
  wordListId: string | null;
  lessonId: string | null;
  topicId: string | null;

  words: Word[]; // Ordered list of words to practice

  progress: {
    current: number; // Cards completed so far
    total: number; // Total cards in session
    correct: number; // Correct answers
    incorrect: number; // Incorrect answers
  };

  startedAt: string; // ISO 8601
  completedAt: string | null;

  // Only in complete response
  masteredWordIds?: string[];
  needsPracticeWordIds?: string[];
}
```

### Pagination

```typescript
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

## Word Lists API

### GET `/v1/word-lists` – List User's Word Lists

Fetch all word lists belonging to the current user.

**Query Parameters:**

| Param      | Type    | Default     | Description                               |
| ---------- | ------- | ----------- | ----------------------------------------- |
| `page`     | number  | 1           | Page number (1-indexed)                   |
| `limit`    | number  | 20          | Items per page (1-100)                    |
| `search`   | string  | -           | Filter by name (partial match)            |
| `favorite` | boolean | -           | Filter favorites only                     |
| `sort`     | string  | `createdAt` | Sort by: `name`, `createdAt`, `updatedAt` |

**Request:**

```http
GET /v1/word-lists?page=1&limit=20&favorite=true
X-User-Id: user-12345
```

**Response (200):**

```json
{
  "data": [
    {
      "id": "wl_abc123",
      "name": "Basic Vocabulary",
      "description": "Common words for beginners",
      "wordCount": 25,
      "isFavorite": true,
      "createdAt": "2025-01-10T08:00:00Z",
      "updatedAt": "2025-01-15T14:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 5
  }
}
```

**Frontend Usage:**

```typescript
// In your word lists screen
const fetchWordLists = async (page = 1, search = "") => {
  const params = new URLSearchParams({ page: String(page), limit: "20" });
  if (search) params.append("search", search);

  const res = await fetch(`/v1/word-lists?${params}`, { headers });
  return res.json();
};
```

---

### POST `/v1/word-lists` – Create Word List

**Request Body:**

```typescript
{
  name: string;           // Required, 1-120 chars
  description?: string;   // Optional
}
```

**Request:**

```http
POST /v1/word-lists
X-User-Id: user-12345
Content-Type: application/json

{
  "name": "Travel Phrases",
  "description": "Useful phrases for traveling"
}
```

**Response (201):**

```json
{
  "id": "wl_new123",
  "name": "Travel Phrases",
  "description": "Useful phrases for traveling",
  "wordCount": 0,
  "isFavorite": false,
  "createdAt": "2025-01-20T10:00:00Z",
  "updatedAt": "2025-01-20T10:00:00Z"
}
```

---

### GET `/v1/word-lists/{listId}` – Get Single Word List

Fetch a word list, optionally with its words.

**Query Parameters:**

| Param      | Type    | Description                             |
| ---------- | ------- | --------------------------------------- |
| `include`  | string  | Set to `words` to include words         |
| `page`     | number  | Page for words (default: 1)             |
| `limit`    | number  | Words per page (default: 100, max: 200) |
| `search`   | string  | Filter words by text                    |
| `favorite` | boolean | Filter favorite words only              |

**Request (with words):**

```http
GET /v1/word-lists/wl_abc123?include=words&page=1&limit=50
X-User-Id: user-12345
```

**Response (200):**

```json
{
  "id": "wl_abc123",
  "name": "Basic Vocabulary",
  "description": "Common words for beginners",
  "wordCount": 25,
  "isFavorite": false,
  "createdAt": "2025-01-10T08:00:00Z",
  "updatedAt": "2025-01-15T14:30:00Z",
  "words": {
    "data": [
      {
        "id": "w_1",
        "word": "Hello",
        "translation": "مرحبا",
        "notes": "Common greeting",
        "isFavorite": false,
        "practiceCount": 5,
        "correctCount": 4,
        "accuracy": 80,
        "lastPracticed": "2025-01-18T09:00:00Z",
        "createdAt": "2025-01-10T08:00:00Z",
        "updatedAt": "2025-01-18T09:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 50,
      "total": 25
    }
  }
}
```

---

### PATCH `/v1/word-lists/{listId}` – Update Word List

**Request Body (all fields optional):**

```typescript
{
  name?: string;
  description?: string;
  isFavorite?: boolean;
}
```

**Request:**

```http
PATCH /v1/word-lists/wl_abc123
X-User-Id: user-12345
Content-Type: application/json

{
  "name": "Updated Name",
  "isFavorite": true
}
```

**Response (200):** Returns updated WordList

---

### DELETE `/v1/word-lists/{listId}` – Delete Word List

**Request:**

```http
DELETE /v1/word-lists/wl_abc123
X-User-Id: user-12345
```

**Response:** `204 No Content`

**Note:** This also deletes all words in the list (cascade delete).

---

### POST `/v1/word-lists/{listId}/favorite` – Toggle Favorite

**Request:**

```http
POST /v1/word-lists/wl_abc123/favorite
X-User-Id: user-12345
Content-Type: application/json

{
  "isFavorite": true
}
```

**Response (200):**

```json
{ "ok": true }
```

---

## Words API

### POST `/v1/word-lists/{listId}/words` – Add Word

**Request Body:**

```typescript
{
  word: string;           // Required, 1-120 chars
  translation: string;    // Required, 1-240 chars
  notes?: string;         // Optional
  isFavorite?: boolean;   // Default: false
}
```

**Request:**

```http
POST /v1/word-lists/wl_abc123/words
X-User-Id: user-12345
Content-Type: application/json

{
  "word": "Goodbye",
  "translation": "مع السلامة",
  "notes": "Formal farewell"
}
```

**Response (201):**

```json
{
  "id": "w_new456",
  "word": "Goodbye",
  "translation": "مع السلامة",
  "notes": "Formal farewell",
  "isFavorite": false,
  "practiceCount": 0,
  "correctCount": 0,
  "accuracy": 0,
  "lastPracticed": null,
  "createdAt": "2025-01-20T10:05:00Z",
  "updatedAt": "2025-01-20T10:05:00Z"
}
```

**Note:** The parent word list's `wordCount` is automatically incremented.

---

### PATCH `/v1/word-lists/{listId}/words/{wordId}` – Update Word

**Request Body (all fields optional):**

```typescript
{
  word?: string;
  translation?: string;
  notes?: string;
  isFavorite?: boolean;
}
```

**Request:**

```http
PATCH /v1/word-lists/wl_abc123/words/w_1
X-User-Id: user-12345
Content-Type: application/json

{
  "translation": "أهلاً",
  "isFavorite": true
}
```

**Response (200):** Returns updated Word

---

### DELETE `/v1/word-lists/{listId}/words/{wordId}` – Delete Word

**Request:**

```http
DELETE /v1/word-lists/wl_abc123/words/w_1
X-User-Id: user-12345
```

**Response:** `204 No Content`

**Note:** The parent word list's `wordCount` is automatically decremented.

---

### POST `/v1/word-lists/{listId}/words/{wordId}/favorite` – Toggle Word Favorite

**Request:**

```http
POST /v1/word-lists/wl_abc123/words/w_1/favorite
X-User-Id: user-12345
Content-Type: application/json

{
  "isFavorite": true
}
```

**Response (200):**

```json
{ "ok": true }
```

---

## Flashcard Sessions API

### POST `/v1/flashcards/sessions` – Start Session

Start a new flashcard practice session.

**Request Body:**

```typescript
{
  mode: 'custom' | 'lesson' | 'topic' | 'mistakes';

  // Required for mode='custom'
  wordListId?: string;
  selectedWordIds?: string[];  // Optional subset of words

  // Required for mode='lesson'
  lessonId?: string;

  // Required for mode='topic'
  topicId?: string;

  // Optional filters
  difficulty?: 'easy' | 'medium' | 'hard';
  shuffle?: boolean;           // Default: false
  limit?: number;              // Max words (1-100, default: 50)
}
```

**Mode Descriptions:**

| Mode       | Description                                        | Required Fields |
| ---------- | -------------------------------------------------- | --------------- |
| `custom`   | Practice user's own word list                      | `wordListId`    |
| `lesson`   | Practice teacher-approved flashcards from a lesson | `lessonId`      |
| `topic`    | Practice teacher-approved flashcards by topic      | `topicId`       |
| `mistakes` | Practice previously incorrect words                | None            |

**Example 1: Custom Mode (User's Word List)**

```http
POST /v1/flashcards/sessions
X-User-Id: user-12345
Content-Type: application/json
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000

{
  "mode": "custom",
  "wordListId": "wl_abc123",
  "shuffle": true
}
```

**Example 2: Custom Mode with Selected Words**

```http
POST /v1/flashcards/sessions
X-User-Id: user-12345
Content-Type: application/json

{
  "mode": "custom",
  "wordListId": "wl_abc123",
  "selectedWordIds": ["w_1", "w_2", "w_3", "w_4", "w_5"],
  "shuffle": false
}
```

**Example 3: Mistakes Mode**

```http
POST /v1/flashcards/sessions
X-User-Id: user-12345
Content-Type: application/json

{
  "mode": "mistakes",
  "limit": 20
}
```

**Response (201):**

```json
{
  "id": "fs_session123",
  "mode": "custom",
  "wordListId": "wl_abc123",
  "lessonId": null,
  "topicId": null,
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
      "lastPracticed": "2025-01-18T09:00:00Z",
      "createdAt": "2025-01-10T08:00:00Z",
      "updatedAt": "2025-01-18T09:00:00Z"
    },
    {
      "id": "w_2",
      "word": "Goodbye",
      "translation": "مع السلامة",
      "notes": null,
      "isFavorite": false,
      "practiceCount": 3,
      "correctCount": 2,
      "accuracy": 67,
      "lastPracticed": "2025-01-17T15:00:00Z",
      "createdAt": "2025-01-10T08:05:00Z",
      "updatedAt": "2025-01-17T15:00:00Z"
    }
  ],
  "progress": {
    "current": 0,
    "total": 10,
    "correct": 0,
    "incorrect": 0
  },
  "startedAt": "2025-01-20T10:00:00Z",
  "completedAt": null
}
```

**Response Headers:**

```
Location: /v1/flashcards/sessions/fs_session123
```

---

### GET `/v1/flashcards/sessions/{sessionId}` – Get Session

Resume or check session state.

**Request:**

```http
GET /v1/flashcards/sessions/fs_session123
X-User-Id: user-12345
```

**Response (200):**

```json
{
  "id": "fs_session123",
  "wordListId": "wl_abc123",
  "words": [...],
  "progress": {
    "current": 5,
    "total": 10,
    "correct": 4,
    "incorrect": 1
  },
  "startedAt": "2025-01-20T10:00:00Z",
  "completedAt": null
}
```

---

### POST `/v1/flashcards/sessions/{sessionId}/results` – Record Result

Record the result for a single flashcard.

**Request Body:**

```typescript
{
  wordId: string;           // Required - the word being answered
  isCorrect: boolean;       // Required - did user get it right?
  timeSpentMs: number;      // Required - milliseconds spent on card (≥0)
  attempts: number;         // Required - number of attempts (≥0)
  clientResultId?: string;  // Optional - for deduplication
}
```

**Request:**

```http
POST /v1/flashcards/sessions/fs_session123/results
X-User-Id: user-12345
Content-Type: application/json
Idempotency-Key: result-uuid-123

{
  "wordId": "w_1",
  "isCorrect": true,
  "timeSpentMs": 1500,
  "attempts": 1,
  "clientResultId": "client-result-abc"
}
```

**Response (200):**

```json
{
  "ok": true,
  "progress": {
    "current": 6,
    "total": 10,
    "correct": 5,
    "incorrect": 1
  },
  "word": {
    "id": "w_1",
    "practiceCount": 6,
    "correctCount": 5,
    "accuracy": 83,
    "lastPracticed": "2025-01-20T10:05:00Z"
  }
}
```

**Side Effects:**

- Word's `practiceCount` incremented
- Word's `correctCount` incremented (if correct)
- Word's `accuracy` recalculated
- Word's `lastPracticed` updated
- Session progress updated
- If incorrect: word added to user's mistakes
- If correct: word removed from mistakes (if present)

**Deduplication:**

- If `clientResultId` was already recorded, returns the existing result
- Use `Idempotency-Key` header for network retry safety

---

### POST `/v1/flashcards/sessions/{sessionId}/complete` – Complete Session

Mark the session as completed.

**Request:**

```http
POST /v1/flashcards/sessions/fs_session123/complete
X-User-Id: user-12345
Content-Type: application/json

{}
```

**Response (200):**

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
  "masteredWordIds": ["w_1", "w_3", "w_5", "w_6", "w_7", "w_8", "w_9", "w_10"],
  "needsPracticeWordIds": ["w_2", "w_4"],
  "startedAt": "2025-01-20T10:00:00Z",
  "completedAt": "2025-01-20T10:15:00Z"
}
```

**Error (409):** If session already completed

```json
{
  "error": {
    "code": "SESSION_COMPLETED",
    "message": "Session already completed"
  }
}
```

---

## Catalog APIs (Topics & Lessons)

These endpoints return teacher-approved flashcard content.

### GET `/v1/flashcards/topics` – List Topics

**Request:**

```http
GET /v1/flashcards/topics
X-User-Id: user-12345
```

**Response (200):**

```json
{
  "topics": [
    {
      "id": "topic_greetings",
      "name": "Greetings",
      "itemCount": 15
    },
    {
      "id": "topic_food",
      "name": "Food & Dining",
      "itemCount": 25
    }
  ]
}
```

---

### GET `/v1/flashcards/lessons` – List Lessons

**Query Parameters:**

| Param     | Type   | Description     |
| --------- | ------ | --------------- |
| `topicId` | string | Filter by topic |

**Request:**

```http
GET /v1/flashcards/lessons?topicId=topic_greetings
X-User-Id: user-12345
```

**Response (200):**

```json
{
  "lessons": [
    {
      "id": "lesson_123",
      "title": "Basic Greetings",
      "lessonDate": "2025-01-15",
      "topicId": "topic_greetings",
      "itemCount": 8
    }
  ]
}
```

---

## Stats & Mistakes APIs

### GET `/v1/flashcards/stats/me` – Get User Stats

**Request:**

```http
GET /v1/flashcards/stats/me
X-User-Id: user-12345
```

**Response (200):**

```json
{
  "totalSessions": 25,
  "completedSessions": 22,
  "totalCorrect": 180,
  "totalIncorrect": 45,
  "accuracy": 80
}
```

---

### GET `/v1/flashcards/mistakes` – List User's Mistakes

**Query Parameters:**

| Param   | Type   | Default | Description            |
| ------- | ------ | ------- | ---------------------- |
| `page`  | number | 1       | Page number            |
| `limit` | number | 50      | Items per page (1-100) |

**Request:**

```http
GET /v1/flashcards/mistakes?page=1&limit=20
X-User-Id: user-12345
```

**Response (200):**

```json
{
  "data": [
    {
      "itemId": "w_2",
      "userAnswer": null,
      "correctAnswer": null,
      "lastAnsweredAt": "2025-01-19T14:30:00Z",
      "word": "Goodbye",
      "translation": "مع السلامة"
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

## Error Handling

### Error Response Format

All errors follow this structure:

```typescript
interface ErrorResponse {
  error: {
    code: string; // Machine-readable error code
    message: string; // Human-readable message
    details?: object; // Additional context
  };
}
```

### Error Codes

| HTTP Status | Code                  | Description                              |
| ----------- | --------------------- | ---------------------------------------- |
| 400         | `VALIDATION_ERROR`    | Invalid request body or parameters       |
| 400         | `UNKNOWN_WORD`        | Word ID not found or not in list         |
| 400         | `NOT_IN_LIST`         | Selected word doesn't belong to the list |
| 404         | `WORD_LIST_NOT_FOUND` | Word list doesn't exist                  |
| 404         | `SESSION_NOT_FOUND`   | Session doesn't exist                    |
| 404         | `LESSON_NOT_FOUND`    | Lesson doesn't exist or not approved     |
| 404         | `TOPIC_NOT_FOUND`     | Topic doesn't exist                      |
| 409         | `SESSION_COMPLETED`   | Session already completed                |
| 409         | `CONFLICT`            | Resource conflict (e.g., duplicate)      |
| 500         | `SERVER_ERROR`        | Internal server error                    |

### Example Error Responses

**Validation Error:**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "wordListId required for custom mode"
  }
}
```

**Unknown Word:**

```json
{
  "error": {
    "code": "UNKNOWN_WORD",
    "message": "Unknown word IDs",
    "details": {
      "invalidIds": ["w_invalid1", "w_invalid2"]
    }
  }
}
```

**Not Found:**

```json
{
  "error": {
    "code": "WORD_LIST_NOT_FOUND",
    "message": "Word list not found"
  }
}
```

### Frontend Error Handling

```typescript
const handleApiError = (error: ErrorResponse) => {
  switch (error.error.code) {
    case "WORD_LIST_NOT_FOUND":
      showToast("This word list no longer exists");
      navigateToWordLists();
      break;
    case "SESSION_COMPLETED":
      showToast("Session already completed");
      navigateToResults();
      break;
    case "VALIDATION_ERROR":
      showToast(error.error.message);
      break;
    default:
      showToast("Something went wrong. Please try again.");
  }
};
```

---

## Complete UI Flow Examples

### Flow 1: Word Lists Screen → Practice

```typescript
// 1. User opens Word Lists screen
const listsResponse = await fetch("/v1/word-lists?page=1&limit=20", {
  headers,
});
const { data: wordLists, pagination } = await listsResponse.json();

// 2. User taps on a list to view words
const listResponse = await fetch(`/v1/word-lists/${listId}?include=words`, {
  headers,
});
const wordList = await listResponse.json();

// 3. User selects some words and taps "Practice"
const sessionResponse = await fetch("/v1/flashcards/sessions", {
  method: "POST",
  headers,
  body: JSON.stringify({
    mode: "custom",
    wordListId: listId,
    selectedWordIds: selectedWords.map((w) => w.id),
    shuffle: true,
  }),
});
const session = await sessionResponse.json();

// 4. Navigate to flashcard practice screen with session data
navigateToFlashcardPractice(session);
```

### Flow 2: Flashcard Practice Screen

```typescript
// State
let currentIndex = 0;
const words = session.words;
const sessionId = session.id;

// User reveals answer and taps "Got it" or "Need practice"
const recordResult = async (isCorrect: boolean, timeSpentMs: number) => {
  const word = words[currentIndex];

  const response = await fetch(`/v1/flashcards/sessions/${sessionId}/results`, {
    method: "POST",
    headers: {
      ...headers,
      "Idempotency-Key": `${sessionId}-${word.id}-${Date.now()}`,
    },
    body: JSON.stringify({
      wordId: word.id,
      isCorrect,
      timeSpentMs,
      attempts: 1,
      clientResultId: `${sessionId}-${word.id}`,
    }),
  });

  const result = await response.json();

  // Update progress UI
  updateProgressBar(result.progress);

  // Move to next card
  currentIndex++;

  if (currentIndex >= words.length) {
    // All cards done, complete session
    await completeSession();
  } else {
    showNextCard(words[currentIndex]);
  }
};

const completeSession = async () => {
  const response = await fetch(
    `/v1/flashcards/sessions/${sessionId}/complete`,
    {
      method: "POST",
      headers,
    }
  );

  const completedSession = await response.json();

  // Navigate to results screen
  navigateToResults({
    correct: completedSession.progress.correct,
    incorrect: completedSession.progress.incorrect,
    accuracy: Math.round(
      (100 * completedSession.progress.correct) /
        completedSession.progress.total
    ),
    masteredWordIds: completedSession.masteredWordIds,
    needsPracticeWordIds: completedSession.needsPracticeWordIds,
  });
};
```

### Flow 3: Creating a New Word List with Words

```typescript
// 1. Create the word list
const listResponse = await fetch("/v1/word-lists", {
  method: "POST",
  headers,
  body: JSON.stringify({
    name: "My New List",
    description: "Words I want to learn",
  }),
});
const newList = await listResponse.json();

// 2. Add words one by one
const wordsToAdd = [
  { word: "Hello", translation: "مرحبا" },
  { word: "Thank you", translation: "شكراً" },
  { word: "Please", translation: "من فضلك" },
];

for (const wordData of wordsToAdd) {
  await fetch(`/v1/word-lists/${newList.id}/words`, {
    method: "POST",
    headers,
    body: JSON.stringify(wordData),
  });
}

// 3. Refresh the list to see updated word count
const updatedList = await fetch(`/v1/word-lists/${newList.id}?include=words`, {
  headers,
});
```

### Flow 4: Practice Mistakes

```typescript
// 1. Check if user has mistakes
const mistakesResponse = await fetch("/v1/flashcards/mistakes?limit=1", {
  headers,
});
const { data: mistakes, pagination } = await mistakesResponse.json();

if (pagination.total === 0) {
  showToast("No mistakes to practice! Great job!");
  return;
}

// 2. Start mistakes session
const sessionResponse = await fetch("/v1/flashcards/sessions", {
  method: "POST",
  headers,
  body: JSON.stringify({
    mode: "mistakes",
    limit: 20,
    shuffle: true,
  }),
});

const session = await sessionResponse.json();
navigateToFlashcardPractice(session);
```

---

## Frontend Service Implementation

Here's a complete TypeScript service implementation:

```typescript
// services/flashcardService.ts

const API_BASE = "https://api.tulkka.com/v1";

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: object;
  idempotencyKey?: string;
}

class FlashcardService {
  private userId: string;

  constructor(userId: string) {
    this.userId = userId;
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-User-Id": this.userId,
    };

    if (options.idempotencyKey) {
      headers["Idempotency-Key"] = options.idempotencyKey;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: options.method || "GET",
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new ApiError(response.status, error.error);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  // ─────────────────────────────────────────────────────────────
  // Word Lists
  // ─────────────────────────────────────────────────────────────

  async getWordLists(
    params: {
      page?: number;
      limit?: number;
      search?: string;
      favorite?: boolean;
      sort?: "name" | "createdAt" | "updatedAt";
    } = {}
  ): Promise<PaginatedResponse<WordList>> {
    const query = new URLSearchParams();
    if (params.page) query.set("page", String(params.page));
    if (params.limit) query.set("limit", String(params.limit));
    if (params.search) query.set("search", params.search);
    if (params.favorite !== undefined)
      query.set("favorite", String(params.favorite));
    if (params.sort) query.set("sort", params.sort);

    return this.request(`/word-lists?${query}`);
  }

  async getWordList(listId: string, includeWords = false): Promise<WordList> {
    const query = includeWords ? "?include=words" : "";
    return this.request(`/word-lists/${listId}${query}`);
  }

  async createWordList(data: {
    name: string;
    description?: string;
  }): Promise<WordList> {
    return this.request("/word-lists", {
      method: "POST",
      body: data,
      idempotencyKey: `create-list-${Date.now()}`,
    });
  }

  async updateWordList(
    listId: string,
    data: Partial<WordList>
  ): Promise<WordList> {
    return this.request(`/word-lists/${listId}`, {
      method: "PATCH",
      body: data,
    });
  }

  async deleteWordList(listId: string): Promise<void> {
    return this.request(`/word-lists/${listId}`, { method: "DELETE" });
  }

  async toggleListFavorite(
    listId: string,
    isFavorite: boolean
  ): Promise<{ ok: boolean }> {
    return this.request(`/word-lists/${listId}/favorite`, {
      method: "POST",
      body: { isFavorite },
    });
  }

  // ─────────────────────────────────────────────────────────────
  // Words
  // ─────────────────────────────────────────────────────────────

  async addWord(
    listId: string,
    data: {
      word: string;
      translation: string;
      notes?: string;
    }
  ): Promise<Word> {
    return this.request(`/word-lists/${listId}/words`, {
      method: "POST",
      body: data,
    });
  }

  async updateWord(
    listId: string,
    wordId: string,
    data: Partial<Word>
  ): Promise<Word> {
    return this.request(`/word-lists/${listId}/words/${wordId}`, {
      method: "PATCH",
      body: data,
    });
  }

  async deleteWord(listId: string, wordId: string): Promise<void> {
    return this.request(`/word-lists/${listId}/words/${wordId}`, {
      method: "DELETE",
    });
  }

  async toggleWordFavorite(
    listId: string,
    wordId: string,
    isFavorite: boolean
  ): Promise<{ ok: boolean }> {
    return this.request(`/word-lists/${listId}/words/${wordId}/favorite`, {
      method: "POST",
      body: { isFavorite },
    });
  }

  // ─────────────────────────────────────────────────────────────
  // Flashcard Sessions
  // ─────────────────────────────────────────────────────────────

  async startSession(params: {
    mode: "custom" | "lesson" | "topic" | "mistakes";
    wordListId?: string;
    selectedWordIds?: string[];
    lessonId?: string;
    topicId?: string;
    difficulty?: "easy" | "medium" | "hard";
    shuffle?: boolean;
    limit?: number;
  }): Promise<FlashcardSession> {
    return this.request("/flashcards/sessions", {
      method: "POST",
      body: params,
      idempotencyKey: `session-${Date.now()}`,
    });
  }

  async getSession(sessionId: string): Promise<FlashcardSession> {
    return this.request(`/flashcards/sessions/${sessionId}`);
  }

  async recordResult(
    sessionId: string,
    data: {
      wordId: string;
      isCorrect: boolean;
      timeSpentMs: number;
      attempts: number;
    }
  ): Promise<{
    ok: boolean;
    progress: Progress;
    word: Partial<Word>;
  }> {
    const clientResultId = `${sessionId}-${data.wordId}`;
    return this.request(`/flashcards/sessions/${sessionId}/results`, {
      method: "POST",
      body: { ...data, clientResultId },
      idempotencyKey: clientResultId,
    });
  }

  async completeSession(sessionId: string): Promise<FlashcardSession> {
    return this.request(`/flashcards/sessions/${sessionId}/complete`, {
      method: "POST",
      body: {},
    });
  }

  // ─────────────────────────────────────────────────────────────
  // Catalog & Stats
  // ─────────────────────────────────────────────────────────────

  async getTopics(): Promise<{ topics: Topic[] }> {
    return this.request("/flashcards/topics");
  }

  async getLessons(topicId?: string): Promise<{ lessons: Lesson[] }> {
    const query = topicId ? `?topicId=${topicId}` : "";
    return this.request(`/flashcards/lessons${query}`);
  }

  async getStats(): Promise<FlashcardStats> {
    return this.request("/flashcards/stats/me");
  }

  async getMistakes(page = 1, limit = 50): Promise<PaginatedResponse<Mistake>> {
    return this.request(`/flashcards/mistakes?page=${page}&limit=${limit}`);
  }
}

// Error class
class ApiError extends Error {
  constructor(
    public status: number,
    public error: { code: string; message: string; details?: object }
  ) {
    super(error.message);
    this.name = "ApiError";
  }
}

// Usage
const flashcardService = new FlashcardService(currentUser.id);

// Get word lists
const lists = await flashcardService.getWordLists({ page: 1, limit: 20 });

// Start a session
const session = await flashcardService.startSession({
  mode: "custom",
  wordListId: "wl_123",
  shuffle: true,
});
```

---

## Best Practices

### 1. Always Use Idempotency Keys

For any POST request that creates or modifies data, include an `Idempotency-Key` header:

```typescript
const idempotencyKey = `${action}-${resourceId}-${Date.now()}`;
headers["Idempotency-Key"] = idempotencyKey;
```

This prevents duplicate operations if the user's network is flaky.

### 2. Use clientResultId for Result Recording

Always include `clientResultId` when recording results to prevent duplicate entries:

```typescript
const clientResultId = `${sessionId}-${wordId}`;
```

### 3. Handle Session Resume

If the app crashes or user navigates away, you can resume:

```typescript
// Store session ID locally
localStorage.setItem("activeFlashcardSession", sessionId);

// On app restart, check for active session
const activeSessionId = localStorage.getItem("activeFlashcardSession");
if (activeSessionId) {
  try {
    const session = await flashcardService.getSession(activeSessionId);
    if (!session.completedAt) {
      // Resume session
      navigateToFlashcardPractice(session);
    }
  } catch (e) {
    // Session not found, clear local storage
    localStorage.removeItem("activeFlashcardSession");
  }
}
```

### 4. Optimistic Updates

For better UX, update UI optimistically:

```typescript
// Optimistically update progress
setProgress(prev => ({
  ...prev,
  current: prev.current + 1,
  correct: isCorrect ? prev.correct + 1 : prev.correct,
  incorrect: !isCorrect ? prev.incorrect + 1 : prev.incorrect
}));

// Then make API call
try {
  const result = await flashcardService.recordResult(sessionId, { ... });
  // Sync with server state if different
  setProgress(result.progress);
} catch (e) {
  // Rollback on error
  setProgress(prev => ({ ... }));
}
```

### 5. Prefetch Next Card Data

While user is viewing current card, prefetch any additional data for the next card if needed.

### 6. Track Time Accurately

Use a timer to track time spent on each card:

```typescript
const startTime = Date.now();

// When user answers
const timeSpentMs = Date.now() - startTime;
await flashcardService.recordResult(sessionId, {
  wordId,
  isCorrect,
  timeSpentMs,
  attempts: 1,
});
```

---

## Summary

| Feature              | Endpoint                                      | Method |
| -------------------- | --------------------------------------------- | ------ |
| List word lists      | `/v1/word-lists`                              | GET    |
| Create word list     | `/v1/word-lists`                              | POST   |
| Get word list        | `/v1/word-lists/{id}`                         | GET    |
| Update word list     | `/v1/word-lists/{id}`                         | PATCH  |
| Delete word list     | `/v1/word-lists/{id}`                         | DELETE |
| Toggle list favorite | `/v1/word-lists/{id}/favorite`                | POST   |
| Add word             | `/v1/word-lists/{id}/words`                   | POST   |
| Update word          | `/v1/word-lists/{id}/words/{wordId}`          | PATCH  |
| Delete word          | `/v1/word-lists/{id}/words/{wordId}`          | DELETE |
| Toggle word favorite | `/v1/word-lists/{id}/words/{wordId}/favorite` | POST   |
| List topics          | `/v1/flashcards/topics`                       | GET    |
| List lessons         | `/v1/flashcards/lessons`                      | GET    |
| Start session        | `/v1/flashcards/sessions`                     | POST   |
| Get session          | `/v1/flashcards/sessions/{id}`                | GET    |
| Record result        | `/v1/flashcards/sessions/{id}/results`        | POST   |
| Complete session     | `/v1/flashcards/sessions/{id}/complete`       | POST   |
| Get stats            | `/v1/flashcards/stats/me`                     | GET    |
| List mistakes        | `/v1/flashcards/mistakes`                     | GET    |

---

**Questions?** Contact the backend team or refer to the test file at `tests/test_flashcards_gameplay.py` for working examples.
