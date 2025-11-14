# Migration Plan: lesson-content-extractor → tulkka-ai

## 🎯 Goal

Complete the tulkka-ai implementation by porting missing components from lesson-content-extractor.

---

## 📊 Current Status

- **Completion:** ~15-20%
- **Missing:** 60/61 API endpoints, extractors, main processor, game routes
- **Working:** Database connections, Zoom workers, basic generators

---

## 🚀 Migration Strategy

### Option A: Full Port (Recommended)

**Time:** 2-3 days  
**Approach:** Port entire `api.py` and core components

### Option B: Incremental Port

**Time:** 1-2 weeks  
**Approach:** Port components one by one

---

## 📋 Phase-by-Phase Plan

### Phase 1: Core API Infrastructure (Day 1 - Critical)

**Priority:** 🔴 CRITICAL  
**Time:** 4-6 hours

#### Tasks:

1. **Port main API file**

   ```bash
   # Copy and adapt api.py structure
   cp lesson-content-extractor/api.py tulkka-ai/src/api/main_api.py
   ```

   **Changes needed:**

   - Update imports to match tulkka-ai structure
   - Integrate with existing `src/api/app.py`
   - Merge middleware configurations
   - Update database connection references

2. **Port SupabaseClient methods**

   ```python
   # Add to src/db/supabase_client.py
   - fetch_transcript()
   - store_exercises()
   - get_exercises()
   - health_check()
   ```

3. **Port ZoomTokenManager**

   ```python
   # Add to src/zoom/zoom_auth.py
   - Auto-refresh logic
   - Token expiry handling
   ```

4. **Add rate limiting**

   ```python
   # Add to requirements.txt
   slowapi==0.1.9

   # Add to src/api/app.py
   from slowapi import Limiter
   ```

5. **Add CORS middleware**
   ```python
   # Add to src/api/app.py
   from fastapi.middleware.cors import CORSMiddleware
   ```

**Verification:**

```bash
# Test endpoints exist
curl http://localhost:8000/docs
# Should show 61 endpoints
```

---

### Phase 2: Content Extraction (Day 1-2 - Critical)

**Priority:** 🔴 CRITICAL  
**Time:** 3-4 hours

#### Tasks:

1. **Create extractors directory**

   ```bash
   mkdir -p tulkka-ai/src/extractors
   ```

2. **Port extractors**

   ```bash
   cp lesson-content-extractor/src/extractors/*.py tulkka-ai/src/extractors/
   ```

   Files to port:

   - `vocabulary_extractor.py` (4689 bytes)
   - `mistake_extractor.py` (4664 bytes)
   - `sentence_extractor.py` (4200 bytes)
   - `__init__.py`

3. **Update imports**
   ```python
   # In each extractor file
   from ..utils.gemini_helper import GeminiHelper
   # Change to:
   from ..ai.gemini_helper import GeminiHelper  # if porting Gemini
   # OR remove Gemini dependency for now
   ```

**Verification:**

```python
from src.extractors import VocabularyExtractor
extractor = VocabularyExtractor()
vocab = extractor.extract("test transcript")
print(vocab)  # Should return list of vocabulary items
```

---

### Phase 3: Main Processor (Day 2 - Critical)

**Priority:** 🔴 CRITICAL  
**Time:** 2-3 hours

#### Tasks:

1. **Port LessonProcessor**

   ```bash
   cp lesson-content-extractor/src/main.py tulkka-ai/src/ai/lesson_processor.py
   ```

2. **Update class structure**

   ```python
   # src/ai/lesson_processor.py
   from ..extractors import VocabularyExtractor, MistakeExtractor, SentenceExtractor
   from .generators import (
       generate_flashcards_from_text,
       generate_cloze_from_text,
       # etc.
   )

   class LessonProcessor:
       def __init__(self):
           self.vocab_extractor = VocabularyExtractor()
           self.mistake_extractor = MistakeExtractor()
           self.sentence_extractor = SentenceExtractor()

       def process_lesson(self, transcript, lesson_number):
           # Port full logic from lesson-content-extractor
           pass
   ```

3. **Integrate with orchestrator**

   ```python
   # Update src/ai/orchestrator.py
   from .lesson_processor import LessonProcessor

   processor = LessonProcessor()

   def process_transcript_to_exercises(summary_row, ...):
       # Use LessonProcessor instead of basic generators
       exercises = processor.process_lesson(
           transcript=summary_row.get("transcript"),
           lesson_number=1
       )
       return exercises
   ```

**Verification:**

```python
from src.ai.lesson_processor import LessonProcessor
processor = LessonProcessor()
result = processor.process_lesson("test transcript", 1)
assert 'fill_in_blank' in result
assert 'flashcards' in result
assert 'spelling' in result
```

---

### Phase 4: Game Routes (Day 2-3 - High Priority)

**Priority:** 🟠 HIGH  
**Time:** 4-6 hours

#### Tasks:

1. **Create game route files**

   ```bash
   cd tulkka-ai/src/games/routes
   # Create missing route files
   touch spelling_routes.py
   touch cloze_routes.py
   touch grammar_routes.py
   touch sentence_routes.py
   touch progress_routes.py
   ```

2. **Port route definitions**
   Extract from `lesson-content-extractor/api.py`:

   - Lines for Spelling endpoints → `spelling_routes.py`
   - Lines for Advanced Cloze → `cloze_routes.py`
   - Lines for Grammar → `grammar_routes.py`
   - Lines for Sentence Builder → `sentence_routes.py`
   - Lines for Progress/Stats → `progress_routes.py`

3. **Register routes**

   ```python
   # src/api/router_root.py
   from ..games.routes import (
       flashcards_routes,
       spelling_routes,
       cloze_routes,
       grammar_routes,
       sentence_routes,
       progress_routes
   )

   router.include_router(flashcards_routes.router)
   router.include_router(spelling_routes.router)
   router.include_router(cloze_routes.router)
   router.include_router(grammar_routes.router)
   router.include_router(sentence_routes.router)
   router.include_router(progress_routes.router)
   ```

**Verification:**

```bash
curl http://localhost:8000/docs
# Should show all 53 game endpoints
```

---

### Phase 5: Lesson Processing Endpoints (Day 3 - High Priority)

**Priority:** 🟠 HIGH  
**Time:** 2-3 hours

#### Tasks:

1. **Create lesson routes**

   ```bash
   touch tulkka-ai/src/api/routes/lesson_routes.py
   ```

2. **Port lesson endpoints**

   ```python
   # src/api/routes/lesson_routes.py
   from fastapi import APIRouter, BackgroundTasks
   from ..ai.lesson_processor import LessonProcessor

   router = APIRouter(prefix="/api/v1", tags=["Lesson Processing"])

   @router.post("/process")
   async def process_transcript(payload: TranscriptInput):
       # Port from lesson-content-extractor/api.py
       pass

   @router.post("/process-multiple")
   async def process_multiple(payload: MultipleTranscriptsInput):
       # Port from lesson-content-extractor/api.py
       pass

   @router.post("/process-zoom-lesson")
   async def process_zoom_lesson(payload: ZoomTranscriptInput, background_tasks: BackgroundTasks):
       # Port from lesson-content-extractor/api.py
       pass
   ```

3. **Register routes**
   ```python
   # src/api/router_root.py
   from .routes import lesson_routes
   router.include_router(lesson_routes.router)
   ```

**Verification:**

```bash
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{"transcript": "test", "lesson_number": 1}'
```

---

### Phase 6: Zoom Integration Endpoints (Day 3 - Medium Priority)

**Priority:** 🟡 MEDIUM  
**Time:** 2 hours

#### Tasks:

1. **Create zoom routes**

   ```bash
   touch tulkka-ai/src/api/routes/zoom_routes.py
   ```

2. **Port zoom endpoints**

   ```python
   # src/api/routes/zoom_routes.py
   from fastapi import APIRouter
   from ..zoom.zoom_client import ZoomAPI

   router = APIRouter(prefix="/api/v1", tags=["Zoom Integration"])

   @router.get("/fetch-zoom-recordings")
   async def fetch_recordings(teacher_email: str, date: str):
       # Port from lesson-content-extractor/api.py
       pass

   @router.get("/zoom-summaries")
   async def get_summaries(class_id: str):
       # Port from lesson-content-extractor/api.py
       pass

   @router.get("/exercises")
   async def get_exercises(class_id: str):
       # Port from lesson-content-extractor/api.py
       pass
   ```

**Verification:**

```bash
curl "http://localhost:8000/api/v1/fetch-zoom-recordings?teacher_email=test@example.com&date=2025-11-15"
```

---

### Phase 7: Quality & Utilities (Day 4 - Medium Priority)

**Priority:** 🟡 MEDIUM  
**Time:** 2-3 hours

#### Tasks:

1. **Port quality checker**

   ```bash
   cp lesson-content-extractor/src/utils/quality_checker.py tulkka-ai/src/ai/quality_checker.py
   ```

2. **Port text processing**

   ```bash
   cp lesson-content-extractor/src/utils/text_processing.py tulkka-ai/src/ai/text_processing.py
   ```

3. **Integrate quality checks**

   ```python
   # src/ai/lesson_processor.py
   from .quality_checker import QualityChecker

   class LessonProcessor:
       def __init__(self):
           # ... existing code ...
           self.quality_checker = QualityChecker()

       def process_lesson(self, transcript, lesson_number):
           # ... generate exercises ...
           is_valid = self.quality_checker.validate_exercises(...)
           return exercises
   ```

---

### Phase 8: AI Enhancement (Optional - Low Priority)

**Priority:** 🟢 LOW  
**Time:** 3-4 hours

#### Tasks:

1. **Port Gemini helper**

   ```bash
   cp lesson-content-extractor/src/utils/gemini_helper.py tulkka-ai/src/ai/gemini_helper.py
   ```

2. **Update generators to use Gemini**

   ```python
   # src/ai/generators.py
   from .gemini_helper import GeminiHelper

   def generate_flashcards_from_text(paragraphs, *, llm_fn=None, ...):
       if not llm_fn:
           gemini = GeminiHelper()
           llm_fn = gemini.generate_content
       # ... rest of logic ...
   ```

---

### Phase 9: Deployment & Documentation (Day 4-5 - Low Priority)

**Priority:** 🟢 LOW  
**Time:** 2-3 hours

#### Tasks:

1. **Create startup scripts**

   ```bash
   # Windows
   cp lesson-content-extractor/start_all.bat tulkka-ai/

   # Linux/Mac
   cp lesson-content-extractor/start_all.sh tulkka-ai/
   chmod +x tulkka-ai/start_all.sh
   ```

2. **Port supervisord config**

   ```bash
   cp lesson-content-extractor/supervisord.conf tulkka-ai/
   ```

3. **Create documentation**
   ```bash
   cp lesson-content-extractor/README.md tulkka-ai/
   cp lesson-content-extractor/README_PRODUCTION.md tulkka-ai/
   # Update with tulkka-ai specific info
   ```

---

## 🔧 Quick Start Commands

### Full Migration (Recommended)

```bash
# 1. Backup current tulkka-ai
cp -r tulkka-ai tulkka-ai-backup

# 2. Create migration branch
cd tulkka-ai
git checkout -b feature/port-lesson-extractor

# 3. Run migration script (create this)
python scripts/migrate_from_lesson_extractor.py

# 4. Test
python -m pytest src/tests/
python src/tests/test_all_endpoints.py

# 5. Start server
python main.py
```

### Manual Migration (Step-by-Step)

```bash
# Day 1: Core API
# 1. Port api.py structure
# 2. Port extractors
# 3. Port LessonProcessor

# Day 2: Routes
# 4. Port game routes
# 5. Port lesson routes

# Day 3: Integration
# 6. Port zoom routes
# 7. Test all endpoints

# Day 4: Polish
# 8. Add quality checker
# 9. Add documentation
# 10. Deploy
```

---

## ✅ Verification Checklist

### After Phase 1 (Core API):

- [ ] Server starts without errors
- [ ] `/docs` shows 61 endpoints
- [ ] Rate limiting works
- [ ] CORS configured
- [ ] MySQL pool connected
- [ ] Supabase client initialized

### After Phase 2 (Extractors):

- [ ] VocabularyExtractor works
- [ ] MistakeExtractor works
- [ ] SentenceExtractor works
- [ ] All return expected data structures

### After Phase 3 (Processor):

- [ ] LessonProcessor instantiates
- [ ] `process_lesson()` returns exercises
- [ ] Exercise counts within 8-12 range
- [ ] Quality validation runs

### After Phase 4 (Game Routes):

- [ ] All 53 game endpoints respond
- [ ] Word lists CRUD works
- [ ] All 5 game types work
- [ ] Sessions flow works

### After Phase 5 (Lesson Routes):

- [ ] `/process` endpoint works
- [ ] `/process-multiple` works
- [ ] `/process-zoom-lesson` works
- [ ] Background tasks execute

### After Phase 6 (Zoom Routes):

- [ ] `/fetch-zoom-recordings` works
- [ ] `/zoom-summaries` works
- [ ] `/exercises` works

### Final Verification:

- [ ] All 61 endpoints tested
- [ ] Integration tests pass
- [ ] Load test passes
- [ ] Documentation complete
- [ ] Deployment scripts work

---

## 🚨 Common Issues & Solutions

### Issue 1: Import Errors

**Problem:** `ModuleNotFoundError: No module named 'src.extractors'`  
**Solution:**

```python
# Add to src/extractors/__init__.py
from .vocabulary_extractor import VocabularyExtractor
from .mistake_extractor import MistakeExtractor
from .sentence_extractor import SentenceExtractor

__all__ = ['VocabularyExtractor', 'MistakeExtractor', 'SentenceExtractor']
```

### Issue 2: Database Connection Errors

**Problem:** MySQL pool not initialized  
**Solution:**

```python
# Check .env file has all required variables
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=password
MYSQL_DATABASE=tulkka9
```

### Issue 3: Zoom Token Errors

**Problem:** 401 Unauthorized from Zoom API  
**Solution:**

```python
# Add refresh token to .env
ZOOM_REFRESH_TOKEN=your_refresh_token

# Verify ZoomTokenManager is used
from src.zoom.zoom_auth import ZoomTokenManager
token_manager = ZoomTokenManager()
token = token_manager.get_token()
```

### Issue 4: Missing Dependencies

**Problem:** `ImportError: cannot import name 'slowapi'`  
**Solution:**

```bash
# Add to requirements.txt
slowapi==0.1.9
assemblyai==0.17.0
google-generativeai==0.3.1

# Install
pip install -r requirements.txt
```

---

## 📊 Progress Tracking

### Day 1:

- [ ] Phase 1: Core API (4-6 hours)
- [ ] Phase 2: Extractors (3-4 hours)

### Day 2:

- [ ] Phase 3: Processor (2-3 hours)
- [ ] Phase 4: Game Routes (4-6 hours)

### Day 3:

- [ ] Phase 5: Lesson Routes (2-3 hours)
- [ ] Phase 6: Zoom Routes (2 hours)

### Day 4:

- [ ] Phase 7: Quality & Utils (2-3 hours)
- [ ] Phase 9: Documentation (2-3 hours)

### Optional:

- [ ] Phase 8: AI Enhancement (3-4 hours)

---

## 🎯 Success Criteria

### Minimum Viable (MVP):

✅ All 61 endpoints working  
✅ Extractors functional  
✅ LessonProcessor working  
✅ Basic tests passing

### Production Ready:

✅ Quality validation enabled  
✅ Comprehensive tests passing  
✅ Documentation complete  
✅ Deployment scripts working

### Enhanced (Optional):

✅ Gemini AI integration  
✅ Advanced quality checks  
✅ Performance optimizations

---

## 📞 Support

### Questions?

- Check `IMPLEMENTATION_COMPARISON.md` for detailed component analysis
- Review `lesson-content-extractor/ACTUAL_STATUS.md` for production status
- Compare file structures between repos

### Testing:

```bash
# Run all tests
python -m pytest src/tests/ -v

# Test specific endpoint
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{"transcript": "test transcript", "lesson_number": 1}'
```

---

**Last Updated:** 2025-11-15  
**Estimated Total Time:** 2-3 days (full migration)  
**Priority:** Complete Phase 1-6 first (critical functionality)
