# Quick Reference: Missing Components

## 🎯 What You Need to Port

### 1. Main API File (CRITICAL)

**Source:** `lesson-content-extractor/api.py` (3196 lines)  
**Target:** `tulkka-ai/src/api/main_api.py`  
**Contains:**

- 61 API endpoints
- MySQL connection pool
- Supabase client methods
- Zoom token manager
- Rate limiting setup
- CORS configuration
- Request logging middleware

**Quick Port:**

```bash
cp lesson-content-extractor/api.py tulkka-ai/src/api/main_api.py
# Then update imports and integrate with existing app.py
```

---

### 2. Extractors (CRITICAL)

**Source:** `lesson-content-extractor/src/extractors/`  
**Target:** `tulkka-ai/src/extractors/`

**Files to copy:**

```bash
mkdir -p tulkka-ai/src/extractors
cp lesson-content-extractor/src/extractors/*.py tulkka-ai/src/extractors/
```

**Files:**

- `vocabulary_extractor.py` (4689 bytes)
- `mistake_extractor.py` (4664 bytes)
- `sentence_extractor.py` (4200 bytes)
- `__init__.py`

---

### 3. Main Processor (CRITICAL)

**Source:** `lesson-content-extractor/src/main.py` (21009 bytes)  
**Target:** `tulkka-ai/src/ai/lesson_processor.py`

**Quick Port:**

```bash
cp lesson-content-extractor/src/main.py tulkka-ai/src/ai/lesson_processor.py
```

**Key Class:**

```python
class LessonProcessor:
    def __init__(self):
        self.vocab_extractor = VocabularyExtractor()
        self.mistake_extractor = MistakeExtractor()
        self.sentence_extractor = SentenceExtractor()
        self.fib_generator = FillInBlankGenerator()
        self.flashcard_generator = FlashcardGenerator()
        self.spelling_generator = SpellingGenerator()
        self.quality_checker = QualityChecker()

    def process_lesson(self, transcript, lesson_number):
        # Full processing logic
        pass
```

---

### 4. Advanced Generators (HIGH PRIORITY)

**Source:** `lesson-content-extractor/src/generators/`  
**Target:** `tulkka-ai/src/ai/generators/`

**Files to copy:**

```bash
mkdir -p tulkka-ai/src/ai/generators
cp lesson-content-extractor/src/generators/*.py tulkka-ai/src/ai/generators/
```

**Files:**

- `advanced_cloze_generator.py` (10956 bytes)
- `grammar_question_generator.py` (13898 bytes)
- `sentence_builder_generator.py` (7159 bytes)
- `fill_in_blank.py` (3356 bytes)
- `flashcard.py` (2371 bytes)
- `spelling.py` (3248 bytes)

---

### 5. Quality Checker (HIGH PRIORITY)

**Source:** `lesson-content-extractor/src/utils/quality_checker.py` (7386 bytes)  
**Target:** `tulkka-ai/src/ai/quality_checker.py`

**Quick Port:**

```bash
cp lesson-content-extractor/src/utils/quality_checker.py tulkka-ai/src/ai/quality_checker.py
```

---

### 6. Utilities (MEDIUM PRIORITY)

**Source:** `lesson-content-extractor/src/utils/`  
**Target:** `tulkka-ai/src/ai/` or `tulkka-ai/src/utils/`

**Files:**

- `gemini_helper.py` (26230 bytes) - AI enhancement
- `text_processing.py` (5799 bytes) - Text utilities

**Quick Port:**

```bash
cp lesson-content-extractor/src/utils/gemini_helper.py tulkka-ai/src/ai/
cp lesson-content-extractor/src/utils/text_processing.py tulkka-ai/src/ai/
```

---

## 📋 Endpoint Mapping

### Lesson Processing Endpoints (3)

**Source:** Lines in `api.py`  
**Target:** `tulkka-ai/src/api/routes/lesson_routes.py`

```python
POST /api/v1/process              # Process single transcript
POST /api/v1/process-multiple     # Process multiple transcripts
POST /api/v1/process-zoom-lesson  # Fetch from Zoom and process
```

---

### Zoom Integration Endpoints (3)

**Source:** Lines in `api.py`  
**Target:** `tulkka-ai/src/api/routes/zoom_routes.py`

```python
GET /api/v1/fetch-zoom-recordings  # Fetch recordings from Zoom
GET /api/v1/zoom-summaries         # Get stored summaries
GET /api/v1/exercises              # Get generated exercises
```

---

### Word Lists Endpoints (11)

**Source:** Lines in `api.py`  
**Target:** `tulkka-ai/src/games/routes/wordlists_routes.py`

```python
GET    /api/v1/word-lists
POST   /api/v1/word-lists
GET    /api/v1/word-lists/{id}
PATCH  /api/v1/word-lists/{id}
DELETE /api/v1/word-lists/{id}
POST   /api/v1/word-lists/{id}/words
GET    /api/v1/word-lists/{id}/words/{word_id}
PATCH  /api/v1/word-lists/{id}/words/{word_id}
DELETE /api/v1/word-lists/{id}/words/{word_id}
GET    /api/v1/word-lists/{id}/export
POST   /api/v1/word-lists/{id}/import
```

---

### Spelling Endpoints (3)

**Source:** Lines in `api.py`  
**Target:** `tulkka-ai/src/games/routes/spelling_routes.py`

```python
POST /api/v1/spelling/sessions
GET  /api/v1/spelling/sessions/{id}
GET  /api/v1/spelling/pronunciation/{word}
```

---

### Advanced Cloze Endpoints (9)

**Source:** Lines in `api.py`  
**Target:** `tulkka-ai/src/games/routes/cloze_routes.py`

```python
GET  /api/v1/advanced-cloze/catalog
GET  /api/v1/advanced-cloze/topics
GET  /api/v1/advanced-cloze/topics/{id}/lessons
POST /api/v1/advanced-cloze/sessions
GET  /api/v1/advanced-cloze/sessions/{id}
POST /api/v1/advanced-cloze/sessions/{id}/results
POST /api/v1/advanced-cloze/sessions/{id}/complete
GET  /api/v1/advanced-cloze/sessions/{id}/hint
GET  /api/v1/advanced-cloze/mistakes
```

---

### Grammar Challenge Endpoints (10)

**Source:** Lines in `api.py`  
**Target:** `tulkka-ai/src/games/routes/grammar_routes.py`

```python
GET  /api/v1/grammar/catalog
GET  /api/v1/grammar/categories
GET  /api/v1/grammar/categories/{id}/lessons
POST /api/v1/grammar/sessions
GET  /api/v1/grammar/sessions/{id}
POST /api/v1/grammar/sessions/{id}/results
POST /api/v1/grammar/sessions/{id}/skip
POST /api/v1/grammar/sessions/{id}/complete
GET  /api/v1/grammar/sessions/{id}/hint
GET  /api/v1/grammar/mistakes
```

---

### Sentence Builder Endpoints (10)

**Source:** Lines in `api.py`  
**Target:** `tulkka-ai/src/games/routes/sentence_routes.py`

```python
GET  /api/v1/sentence-builder/catalog
GET  /api/v1/sentence-builder/topics
GET  /api/v1/sentence-builder/topics/{id}/lessons
POST /api/v1/sentence-builder/sessions
GET  /api/v1/sentence-builder/sessions/{id}
POST /api/v1/sentence-builder/sessions/{id}/results
POST /api/v1/sentence-builder/sessions/{id}/complete
GET  /api/v1/sentence-builder/sessions/{id}/hint
GET  /api/v1/sentence-builder/tts/{text}
GET  /api/v1/sentence-builder/mistakes
```

---

### Progress & Stats Endpoints (8)

**Source:** Lines in `api.py`  
**Target:** `tulkka-ai/src/games/routes/progress_routes.py`

```python
GET /api/v1/progress/me
GET /api/v1/progress/class/{class_id}
GET /api/v1/stats/me
GET /api/v1/stats/class/{class_id}
GET /api/v1/mistakes/me
GET /api/v1/mistakes/class/{class_id}
GET /health
GET /
```

---

## 🔧 Database Methods to Add

### Supabase Client Methods

**File:** `tulkka-ai/src/db/supabase_client.py`

**Add these methods:**

```python
class SupabaseClient:
    def fetch_transcript(self, user_id, teacher_id, class_id, date,
                        meeting_time=None, start_time=None, end_time=None):
        """Fetch transcript from zoom_summaries with time filtering"""
        pass

    def store_exercises(self, user_id, teacher_id, class_id,
                       lesson_number, exercises, zoom_summary_id=None):
        """Store generated exercises in lesson_exercises table"""
        pass

    def get_exercises(self, class_id, user_id=None):
        """Retrieve exercises for a class"""
        pass

    def health_check(self):
        """Check Supabase connection"""
        pass
```

**Source:** Lines 105-246 in `lesson-content-extractor/api.py`

---

### MySQL Helper Functions

**File:** `tulkka-ai/src/db/mysql_pool.py`

**Add this function:**

```python
def execute_query(query: str, params: tuple = None,
                 fetch_one: bool = False, fetch_all: bool = True):
    """Helper to execute MySQL queries with proper error handling"""
    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(query, params or ())

        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = cursor.rowcount

        cursor.close()
        conn.close()
        return result

    except MySQLError as e:
        conn.rollback()
        cursor.close()
        conn.close()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
```

**Source:** Lines 297-323 in `lesson-content-extractor/api.py`

---

## 🚀 Quick Migration Script

Create `tulkka-ai/scripts/quick_migrate.py`:

```python
#!/usr/bin/env python3
"""Quick migration script to copy essential files"""

import shutil
from pathlib import Path

SOURCE = Path("../lesson-content-extractor")
TARGET = Path(".")

# 1. Copy extractors
print("Copying extractors...")
shutil.copytree(
    SOURCE / "src/extractors",
    TARGET / "src/extractors",
    dirs_exist_ok=True
)

# 2. Copy main processor
print("Copying main processor...")
shutil.copy(
    SOURCE / "src/main.py",
    TARGET / "src/ai/lesson_processor.py"
)

# 3. Copy generators
print("Copying generators...")
shutil.copytree(
    SOURCE / "src/generators",
    TARGET / "src/ai/generators",
    dirs_exist_ok=True
)

# 4. Copy quality checker
print("Copying quality checker...")
shutil.copy(
    SOURCE / "src/utils/quality_checker.py",
    TARGET / "src/ai/quality_checker.py"
)

# 5. Copy utilities
print("Copying utilities...")
for util in ["gemini_helper.py", "text_processing.py"]:
    shutil.copy(
        SOURCE / f"src/utils/{util}",
        TARGET / f"src/ai/{util}"
    )

print("\n✅ Core files copied!")
print("\nNext steps:")
print("1. Update imports in copied files")
print("2. Port api.py endpoints")
print("3. Create game route files")
print("4. Test endpoints")
```

**Run:**

```bash
cd tulkka-ai
python scripts/quick_migrate.py
```

---

## 📦 Dependencies to Add

**File:** `tulkka-ai/requirements.txt`

**Add these:**

```txt
# Rate limiting
slowapi==0.1.9

# AI Enhancement (optional)
google-generativeai==0.3.1

# Already have:
# assemblyai==0.17.0
# fastapi
# uvicorn
# mysql-connector-python
# supabase
# python-dotenv
```

**Install:**

```bash
pip install -r requirements.txt
```

---

## ✅ Quick Verification Commands

### Test API is running:

```bash
curl http://localhost:8000/health
```

### Test endpoint count:

```bash
curl http://localhost:8000/docs | grep -o "operationId" | wc -l
# Should show 61
```

### Test lesson processing:

```bash
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "Today we learned about present perfect tense. The student made a mistake with have vs has.",
    "lesson_number": 1
  }'
```

### Test extractors:

```python
from src.extractors import VocabularyExtractor
extractor = VocabularyExtractor()
vocab = extractor.extract("test transcript")
print(vocab)
```

### Test processor:

```python
from src.ai.lesson_processor import LessonProcessor
processor = LessonProcessor()
result = processor.process_lesson("test transcript", 1)
print(result.keys())  # Should have: fill_in_blank, flashcards, spelling
```

---

## 🎯 Priority Order

### Do First (Critical):

1. ✅ Copy extractors
2. ✅ Copy main processor
3. ✅ Port api.py structure
4. ✅ Add Supabase methods
5. ✅ Create game routes

### Do Second (High):

6. ✅ Copy quality checker
7. ✅ Copy advanced generators
8. ✅ Add lesson routes
9. ✅ Add zoom routes
10. ✅ Test all endpoints

### Do Third (Medium):

11. ✅ Copy utilities
12. ✅ Add documentation
13. ✅ Create startup scripts
14. ✅ Add comprehensive tests

### Optional (Low):

15. ⭕ Add Gemini AI enhancement
16. ⭕ Performance optimizations
17. ⭕ Advanced features

---

## 📞 Quick Help

### Can't find a file?

```bash
# Search in lesson-content-extractor
cd lesson-content-extractor
find . -name "*.py" | grep -i "keyword"
```

### Import errors?

```python
# Add to __init__.py files
from .module_name import ClassName
__all__ = ['ClassName']
```

### Database errors?

```bash
# Check .env file
cat .env | grep MYSQL
cat .env | grep SUPABASE
```

### Endpoint not showing?

```python
# Check router registration in app.py
app.include_router(router_name.router)
```

---

**Last Updated:** 2025-11-15  
**See Also:**

- `IMPLEMENTATION_COMPARISON.md` - Detailed analysis
- `MIGRATION_PLAN.md` - Step-by-step guide
