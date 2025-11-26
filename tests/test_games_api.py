"""
Comprehensive Tests for TULKKA Games APIs
Tests all 5 games: Flashcards, Spelling Bee, Grammar Challenge, Advanced Cloze, Sentence Builder
"""

import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from src.api.app import app


# =============================================================================
# Test Configuration
# =============================================================================

@pytest.fixture
def test_user_id():
    return f"test-user-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def headers(test_user_id):
    return {"X-User-Id": test_user_id, "Content-Type": "application/json"}


@pytest_asyncio.fixture(scope="function")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# =============================================================================
# 1. FLASHCARDS & WORD LISTS TESTS
# =============================================================================

class TestWordLists:
    """Test Word Lists CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_word_list(self, client, headers):
        """POST /v1/word-lists - Create a new word list."""
        response = await client.post(
            "/v1/word-lists",
            headers=headers,
            json={"name": "Test Vocabulary", "description": "Test description"}
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Vocabulary"
        assert data["wordCount"] == 0
        return data["id"]
    
    @pytest.mark.asyncio
    async def test_list_word_lists(self, client, headers):
        """GET /v1/word-lists - List user's word lists."""
        response = await client.get("/v1/word-lists", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert "page" in data["pagination"]
        assert "limit" in data["pagination"]
        assert "total" in data["pagination"]
    
    @pytest.mark.asyncio
    async def test_list_word_lists_with_search(self, client, headers):
        """GET /v1/word-lists?search=... - Search word lists."""
        response = await client.get("/v1/word-lists?search=test", headers=headers)
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_list_word_lists_with_pagination(self, client, headers):
        """GET /v1/word-lists?page=1&limit=10 - Paginated word lists."""
        response = await client.get("/v1/word-lists?page=1&limit=10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 10


class TestWordListsCRUD:
    """Test complete Word Lists CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_get_word_list(self, client, headers):
        """GET /v1/word-lists/{listId} - Get a specific word list."""
        # Create a list first
        create_response = await client.post(
            "/v1/word-lists",
            headers=headers,
            json={"name": "Get Test List", "description": "Test"}
        )
        list_id = create_response.json()["id"]
        
        # Get the list
        response = await client.get(f"/v1/word-lists/{list_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == list_id
        assert data["name"] == "Get Test List"
    
    @pytest.mark.asyncio
    async def test_get_word_list_with_words(self, client, headers):
        """GET /v1/word-lists/{listId}?include=words - Get list with words."""
        # Create list and add word
        create_response = await client.post(
            "/v1/word-lists",
            headers=headers,
            json={"name": "List With Words"}
        )
        list_id = create_response.json()["id"]
        
        await client.post(
            f"/v1/word-lists/{list_id}/words",
            headers=headers,
            json={"word": "test", "translation": "اختبار"}
        )
        
        # Get with words
        response = await client.get(f"/v1/word-lists/{list_id}?include=words", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "words" in data
        assert "data" in data["words"]
        assert "pagination" in data["words"]
    
    @pytest.mark.asyncio
    async def test_update_word_list(self, client, headers):
        """PATCH /v1/word-lists/{listId} - Update a word list."""
        # Create a list
        create_response = await client.post(
            "/v1/word-lists",
            headers=headers,
            json={"name": "Original Name"}
        )
        list_id = create_response.json()["id"]
        
        # Update the list
        response = await client.patch(
            f"/v1/word-lists/{list_id}",
            headers=headers,
            json={"name": "Updated Name", "description": "New description"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "New description"
    
    @pytest.mark.asyncio
    async def test_delete_word_list(self, client, headers):
        """DELETE /v1/word-lists/{listId} - Delete a word list."""
        # Create a list
        create_response = await client.post(
            "/v1/word-lists",
            headers=headers,
            json={"name": "To Delete"}
        )
        list_id = create_response.json()["id"]
        
        # Delete the list
        response = await client.delete(f"/v1/word-lists/{list_id}", headers=headers)
        assert response.status_code == 204
        
        # Verify it's deleted
        get_response = await client.get(f"/v1/word-lists/{list_id}", headers=headers)
        assert get_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_toggle_list_favorite(self, client, headers):
        """POST /v1/word-lists/{listId}/favorite - Toggle favorite."""
        # Create a list
        create_response = await client.post(
            "/v1/word-lists",
            headers=headers,
            json={"name": "Favorite Test"}
        )
        list_id = create_response.json()["id"]
        
        # Toggle favorite
        response = await client.post(
            f"/v1/word-lists/{list_id}/favorite",
            headers=headers,
            json={"isFavorite": True}
        )
        assert response.status_code == 200
        assert response.json()["ok"] == True


class TestWords:
    """Test Words CRUD operations within word lists."""
    
    @pytest.mark.asyncio
    async def test_create_word(self, client, headers):
        """POST /v1/word-lists/{listId}/words - Add a word."""
        # First create a list
        list_response = await client.post(
            "/v1/word-lists",
            headers=headers,
            json={"name": "Words Test List"}
        )
        list_id = list_response.json()["id"]
        
        # Add a word
        response = await client.post(
            f"/v1/word-lists/{list_id}/words",
            headers=headers,
            json={"word": "hello", "translation": "مرحبا", "notes": "greeting"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["word"] == "hello"
        assert data["translation"] == "مرحبا"
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_update_word(self, client, headers):
        """PATCH /v1/word-lists/{listId}/words/{wordId} - Update a word."""
        # Create list and word
        list_response = await client.post(
            "/v1/word-lists",
            headers=headers,
            json={"name": "Update Word Test"}
        )
        list_id = list_response.json()["id"]
        
        word_response = await client.post(
            f"/v1/word-lists/{list_id}/words",
            headers=headers,
            json={"word": "original", "translation": "أصلي"}
        )
        word_id = word_response.json()["id"]
        
        # Update the word
        response = await client.patch(
            f"/v1/word-lists/{list_id}/words/{word_id}",
            headers=headers,
            json={"word": "updated", "translation": "محدث"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["word"] == "updated"
        assert data["translation"] == "محدث"
    
    @pytest.mark.asyncio
    async def test_delete_word(self, client, headers):
        """DELETE /v1/word-lists/{listId}/words/{wordId} - Delete a word."""
        # Create list and word
        list_response = await client.post(
            "/v1/word-lists",
            headers=headers,
            json={"name": "Delete Word Test"}
        )
        list_id = list_response.json()["id"]
        
        word_response = await client.post(
            f"/v1/word-lists/{list_id}/words",
            headers=headers,
            json={"word": "to_delete", "translation": "للحذف"}
        )
        word_id = word_response.json()["id"]
        
        # Delete the word
        response = await client.delete(
            f"/v1/word-lists/{list_id}/words/{word_id}",
            headers=headers
        )
        assert response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_toggle_word_favorite(self, client, headers):
        """POST /v1/word-lists/{listId}/words/{wordId}/favorite - Toggle word favorite."""
        # Create list and word
        list_response = await client.post(
            "/v1/word-lists",
            headers=headers,
            json={"name": "Word Favorite Test"}
        )
        list_id = list_response.json()["id"]
        
        word_response = await client.post(
            f"/v1/word-lists/{list_id}/words",
            headers=headers,
            json={"word": "favorite", "translation": "مفضل"}
        )
        word_id = word_response.json()["id"]
        
        # Toggle favorite
        response = await client.post(
            f"/v1/word-lists/{list_id}/words/{word_id}/favorite",
            headers=headers,
            json={"isFavorite": True}
        )
        assert response.status_code == 200
        assert response.json()["ok"] == True


class TestFlashcardSessions:
    """Test Flashcard session lifecycle."""
    
    @pytest.mark.asyncio
    async def test_start_flashcard_session(self, client, headers):
        """POST /v1/flashcards/sessions - Start a session."""
        # Create list with words first
        list_response = await client.post(
            "/v1/word-lists",
            headers=headers,
            json={"name": "Flashcard Test"}
        )
        list_id = list_response.json()["id"]
        
        # Add words
        for word, trans in [("cat", "قطة"), ("dog", "كلب")]:
            await client.post(
                f"/v1/word-lists/{list_id}/words",
                headers=headers,
                json={"word": word, "translation": trans}
            )
        
        # Start session
        response = await client.post(
            "/v1/flashcards/sessions",
            headers=headers,
            json={"wordListId": list_id}
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "words" in data
        assert "progress" in data
        assert data["progress"]["current"] == 0
        assert data["progress"]["total"] == 2
    
    @pytest.mark.asyncio
    async def test_flashcard_session_not_found(self, client, headers):
        """GET /v1/flashcards/sessions/{id} - Session not found."""
        response = await client.get(
            "/v1/flashcards/sessions/nonexistent-session",
            headers=headers
        )
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_flashcard_session(self, client, headers):
        """GET /v1/flashcards/sessions/{sessionId} - Get session for resume."""
        # Create list with words
        list_response = await client.post(
            "/v1/word-lists",
            headers=headers,
            json={"name": "Get Session Test"}
        )
        list_id = list_response.json()["id"]
        
        await client.post(
            f"/v1/word-lists/{list_id}/words",
            headers=headers,
            json={"word": "test", "translation": "اختبار"}
        )
        
        # Start session
        session_response = await client.post(
            "/v1/flashcards/sessions",
            headers=headers,
            json={"wordListId": list_id}
        )
        session_id = session_response.json()["id"]
        
        # Get session
        response = await client.get(
            f"/v1/flashcards/sessions/{session_id}",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert "words" in data
        assert "progress" in data
    
    @pytest.mark.asyncio
    async def test_record_flashcard_result(self, client, headers):
        """POST /v1/flashcards/sessions/{sessionId}/results - Record result."""
        # Create list with words
        list_response = await client.post(
            "/v1/word-lists",
            headers=headers,
            json={"name": "Result Test"}
        )
        list_id = list_response.json()["id"]
        
        word_response = await client.post(
            f"/v1/word-lists/{list_id}/words",
            headers=headers,
            json={"word": "apple", "translation": "تفاحة"}
        )
        word_id = word_response.json()["id"]
        
        # Start session
        session_response = await client.post(
            "/v1/flashcards/sessions",
            headers=headers,
            json={"wordListId": list_id}
        )
        session_id = session_response.json()["id"]
        
        # Record result
        response = await client.post(
            f"/v1/flashcards/sessions/{session_id}/results",
            headers=headers,
            json={
                "wordId": word_id,
                "isCorrect": True,
                "timeSpentMs": 1500,
                "attempts": 1
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert "progress" in data
        assert data["progress"]["correct"] == 1
    
    @pytest.mark.asyncio
    async def test_complete_flashcard_session(self, client, headers):
        """POST /v1/flashcards/sessions/{sessionId}/complete - Complete session."""
        # Create list with words
        list_response = await client.post(
            "/v1/word-lists",
            headers=headers,
            json={"name": "Complete Test"}
        )
        list_id = list_response.json()["id"]
        
        await client.post(
            f"/v1/word-lists/{list_id}/words",
            headers=headers,
            json={"word": "finish", "translation": "انتهى"}
        )
        
        # Start session
        session_response = await client.post(
            "/v1/flashcards/sessions",
            headers=headers,
            json={"wordListId": list_id}
        )
        session_id = session_response.json()["id"]
        
        # Complete session
        response = await client.post(
            f"/v1/flashcards/sessions/{session_id}/complete",
            headers=headers,
            json={}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["completedAt"] is not None
    
    @pytest.mark.asyncio
    async def test_flashcard_stats(self, client, headers):
        """GET /v1/flashcards/stats/me - Get user stats."""
        response = await client.get("/v1/flashcards/stats/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "totalSessions" in data
        assert "accuracy" in data


# =============================================================================
# 2. SPELLING BEE TESTS
# =============================================================================

class TestSpellingSessions:
    """Test Spelling Bee session lifecycle."""
    
    @pytest.mark.asyncio
    async def test_start_spelling_session(self, client, headers):
        """POST /v1/spelling/sessions - Start a spelling session."""
        # Create list with words first
        list_response = await client.post(
            "/v1/word-lists",
            headers=headers,
            json={"name": "Spelling Test"}
        )
        list_id = list_response.json()["id"]
        
        # Add words
        for word, trans in [("beautiful", "جميل"), ("elephant", "فيل")]:
            await client.post(
                f"/v1/word-lists/{list_id}/words",
                headers=headers,
                json={"word": word, "translation": trans}
            )
        
        # Start session
        response = await client.post(
            "/v1/spelling/sessions",
            headers=headers,
            json={"wordListId": list_id, "shuffle": True}
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "words" in data
        assert "progress" in data
    
    @pytest.mark.asyncio
    async def test_spelling_stats(self, client, headers):
        """GET /v1/spelling/stats/me - Get user stats."""
        response = await client.get("/v1/spelling/stats/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "totalSessions" in data
        assert "accuracy" in data
    
    @pytest.mark.asyncio
    async def test_spelling_mistakes(self, client, headers):
        """GET /v1/spelling/mistakes - Get user mistakes."""
        response = await client.get("/v1/spelling/mistakes", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data


# =============================================================================
# 3. GRAMMAR CHALLENGE TESTS
# =============================================================================

class TestGrammarChallenge:
    """Test Grammar Challenge endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_categories(self, client, headers):
        """GET /v1/grammar-challenge/categories - Get grammar categories."""
        response = await client.get("/v1/grammar-challenge/categories", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
    
    @pytest.mark.asyncio
    async def test_get_lessons(self, client, headers):
        """GET /v1/grammar-challenge/lessons - Get grammar lessons."""
        response = await client.get("/v1/grammar-challenge/lessons", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
    
    @pytest.mark.asyncio
    async def test_get_questions(self, client, headers):
        """GET /v1/grammar-challenge/questions - Get grammar questions."""
        response = await client.get("/v1/grammar-challenge/questions", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
    
    @pytest.mark.asyncio
    async def test_grammar_stats(self, client, headers):
        """GET /v1/grammar-challenge/stats/me - Get user stats."""
        response = await client.get("/v1/grammar-challenge/stats/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "totalSessions" in data
    
    @pytest.mark.asyncio
    async def test_grammar_mistakes(self, client, headers):
        """GET /v1/grammar-challenge/mistakes - Get user mistakes."""
        response = await client.get("/v1/grammar-challenge/mistakes", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data


# =============================================================================
# 4. ADVANCED CLOZE TESTS
# =============================================================================

class TestAdvancedCloze:
    """Test Advanced Cloze endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_topics(self, client, headers):
        """GET /v1/advanced-cloze/topics - Get cloze topics."""
        response = await client.get("/v1/advanced-cloze/topics", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
    
    @pytest.mark.asyncio
    async def test_get_lessons(self, client, headers):
        """GET /v1/advanced-cloze/lessons - Get cloze lessons."""
        response = await client.get("/v1/advanced-cloze/lessons", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
    
    @pytest.mark.asyncio
    async def test_get_items(self, client, headers):
        """GET /v1/advanced-cloze/items - Get cloze items."""
        response = await client.get("/v1/advanced-cloze/items", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
    
    @pytest.mark.asyncio
    async def test_cloze_stats(self, client, headers):
        """GET /v1/advanced-cloze/stats/me - Get user stats."""
        response = await client.get("/v1/advanced-cloze/stats/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "totalSessions" in data
    
    @pytest.mark.asyncio
    async def test_cloze_mistakes(self, client, headers):
        """GET /v1/advanced-cloze/mistakes - Get user mistakes."""
        response = await client.get("/v1/advanced-cloze/mistakes", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data


# =============================================================================
# 5. SENTENCE BUILDER TESTS
# =============================================================================

class TestSentenceBuilder:
    """Test Sentence Builder endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_topics(self, client, headers):
        """GET /v1/sentence-builder/topics - Get sentence topics."""
        response = await client.get("/v1/sentence-builder/topics", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
    
    @pytest.mark.asyncio
    async def test_get_lessons(self, client, headers):
        """GET /v1/sentence-builder/lessons - Get sentence lessons."""
        response = await client.get("/v1/sentence-builder/lessons", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
    
    @pytest.mark.asyncio
    async def test_get_items(self, client, headers):
        """GET /v1/sentence-builder/items - Get sentence items."""
        response = await client.get("/v1/sentence-builder/items", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
    
    @pytest.mark.asyncio
    async def test_sentence_stats(self, client, headers):
        """GET /v1/sentence-builder/stats/me - Get user stats."""
        response = await client.get("/v1/sentence-builder/stats/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "totalSessions" in data
    
    @pytest.mark.asyncio
    async def test_sentence_mistakes(self, client, headers):
        """GET /v1/sentence-builder/mistakes - Get user mistakes."""
        response = await client.get("/v1/sentence-builder/mistakes", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Test error responses match spec."""
    
    @pytest.mark.asyncio
    async def test_word_list_not_found(self, client, headers):
        """Test 404 error for non-existent word list."""
        response = await client.get(
            "/v1/word-lists/nonexistent-list-id",
            headers=headers
        )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_validation_error(self, client, headers):
        """Test 400 error for invalid request."""
        response = await client.post(
            "/v1/word-lists",
            headers=headers,
            json={"name": ""}  # Empty name should fail
        )
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_session_not_found(self, client, headers):
        """Test 404 error for non-existent session."""
        response = await client.get(
            "/v1/flashcards/sessions/nonexistent",
            headers=headers
        )
        assert response.status_code == 404


# =============================================================================
# IDEMPOTENCY TESTS
# =============================================================================

class TestIdempotency:
    """Test idempotency key support."""
    
    @pytest.mark.asyncio
    async def test_idempotent_word_list_creation(self, client, headers):
        """Test idempotent word list creation."""
        idempotency_key = str(uuid.uuid4())
        headers_with_key = {**headers, "Idempotency-Key": idempotency_key}
        
        # First request
        response1 = await client.post(
            "/v1/word-lists",
            headers=headers_with_key,
            json={"name": "Idempotent Test"}
        )
        assert response1.status_code == 201
        
        # Second request with same key should return same result
        response2 = await client.post(
            "/v1/word-lists",
            headers=headers_with_key,
            json={"name": "Idempotent Test"}
        )
        # Should either return 201 with same data or handle idempotency
        assert response2.status_code in [201, 200]


# =============================================================================
# PAGINATION TESTS
# =============================================================================

class TestPagination:
    """Test pagination across all endpoints."""
    
    @pytest.mark.asyncio
    async def test_word_lists_pagination_format(self, client, headers):
        """Test pagination response format."""
        response = await client.get("/v1/word-lists?page=1&limit=5", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        pagination = data["pagination"]
        assert "page" in pagination
        assert "limit" in pagination
        assert "total" in pagination
        assert pagination["page"] == 1
        assert pagination["limit"] == 5
    
    @pytest.mark.asyncio
    async def test_grammar_questions_pagination(self, client, headers):
        """Test grammar questions pagination."""
        response = await client.get(
            "/v1/grammar-challenge/questions?page=1&limit=10",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
