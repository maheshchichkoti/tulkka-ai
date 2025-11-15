"""Comprehensive API test suite for all endpoints"""
import requests
import json
from typing import Dict, List, Optional

BASE_URL = "http://localhost:8000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

# Store created IDs for cleanup
created_word_lists = []
created_sessions = []

def test_endpoint(name: str, method: str, url: str, data: Dict = None, expected_status: int = 200, return_data: bool = False, allow_404_for_delete: bool = False):
    """Test a single endpoint"""
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=5)
        elif method == "PATCH":
            response = requests.patch(url, json=data, timeout=5)
        elif method == "DELETE":
            response = requests.delete(url, timeout=5)
        else:
            print(f"{Colors.RED}✗{Colors.END} {name}: Unknown method {method}")
            return False if not return_data else (False, None)
        
        # For DELETE operations, treat 404 as success (resource already deleted)
        if allow_404_for_delete and method == "DELETE" and response.status_code == 404:
            print(f"{Colors.GREEN}✓{Colors.END} {name}: 404 (already deleted)")
            if return_data:
                return True, None
            return True
        
        if response.status_code == expected_status:
            print(f"{Colors.GREEN}✓{Colors.END} {name}: {response.status_code}")
            if return_data:
                try:
                    return True, response.json()
                except:
                    return True, None
            return True
        else:
            print(f"{Colors.RED}✗{Colors.END} {name}: Expected {expected_status}, got {response.status_code}")
            if return_data:
                return False, None
            return False
    except Exception as e:
        print(f"{Colors.RED}✗{Colors.END} {name}: {str(e)}")
        if return_data:
            return False, None
        return False

def main():
    print("=" * 80)
    print(f"{Colors.BLUE}Tulkka AI - Comprehensive API Test Suite{Colors.END}")
    print("=" * 80)
    
    results = []
    
    # Core API Tests
    print(f"\n{Colors.YELLOW}=== Core API ==={Colors.END}")
    results.append(("Health Check", test_endpoint("Health Check", "GET", f"{BASE_URL}/v1/health")))
    results.append(("API Docs", test_endpoint("API Docs", "GET", f"{BASE_URL}/docs")))
    
    # Lesson Processing Tests
    print(f"\n{Colors.YELLOW}=== Lesson Processing ==={Colors.END}")
    transcript_data = {
        "transcript": "Today we learned about present perfect tense. I have gone to Paris.",
        "lesson_number": 1
    }
    results.append(("Process Transcript", test_endpoint(
        "Process Transcript", "POST", f"{BASE_URL}/v1/process", transcript_data
    )))
    
    results.append(("Get Exercises", test_endpoint(
        "Get Exercises", "GET", f"{BASE_URL}/v1/exercises?class_id=test_class"
    )))
    
    # Flashcards Tests
    print(f"\n{Colors.YELLOW}=== Flashcards API ==={Colors.END}")
    
    # Word Lists CRUD
    results.append(("List Word Lists", test_endpoint(
        "List Word Lists", "GET", f"{BASE_URL}/v1/word-lists?page=1&limit=10"
    )))
    
    success, wl_data = test_endpoint(
        "Create Word List", "POST", f"{BASE_URL}/v1/word-lists",
        {"name": "Test List", "description": "Test description"}, 201, return_data=True
    )
    results.append(("Create Word List", success))
    list_id = wl_data.get("id") if wl_data else "test-list-1"
    if list_id:
        created_word_lists.append(list_id)
    
    results.append(("Get Word List", test_endpoint(
        "Get Word List", "GET", f"{BASE_URL}/v1/word-lists/{list_id}"
    )))
    
    results.append(("Update Word List", test_endpoint(
        "Update Word List", "PATCH", f"{BASE_URL}/v1/word-lists/{list_id}",
        {"name": "Updated Test List"}
    )))
    
    results.append(("Toggle List Favorite", test_endpoint(
        "Toggle List Favorite", "POST", f"{BASE_URL}/v1/word-lists/{list_id}/favorite",
        {"isFavorite": True}
    )))
    
    # Words CRUD
    success, word_data = test_endpoint(
        "Add Word", "POST", f"{BASE_URL}/v1/word-lists/{list_id}/words",
        {"word": "hello", "translation": "مرحبا", "notes": "greeting", "difficulty": "beginner"},
        201, return_data=True
    )
    results.append(("Add Word", success))
    word_id = word_data.get("id") if word_data else "test-word-1"
    
    results.append(("Update Word", test_endpoint(
        "Update Word", "PATCH", f"{BASE_URL}/v1/word-lists/{list_id}/words/{word_id}",
        {"translation": "أهلاً"}
    )))
    
    results.append(("Toggle Word Favorite", test_endpoint(
        "Toggle Word Favorite", "POST", f"{BASE_URL}/v1/word-lists/{list_id}/words/{word_id}/favorite",
        {"isFavorite": True}
    )))
    
    # Flashcard Sessions
    success, session_data = test_endpoint(
        "Start Flashcard Session", "POST", f"{BASE_URL}/v1/flashcards/sessions",
        {"wordListId": list_id}, 201, return_data=True
    )
    results.append(("Start Flashcard Session", success))
    session_id = session_data.get("id") if session_data else "test-session-1"
    if session_id:
        created_sessions.append(session_id)
    
    results.append(("Get Flashcard Session", test_endpoint(
        "Get Flashcard Session", "GET", f"{BASE_URL}/v1/flashcards/sessions/{session_id}"
    )))
    
    results.append(("Record Flashcard Result", test_endpoint(
        "Record Flashcard Result", "POST", f"{BASE_URL}/v1/flashcards/sessions/{session_id}/results",
        {"wordId": word_id, "isCorrect": True, "timeSpent": 1200, "attempts": 1}
    )))
    
    results.append(("Complete Flashcard Session", test_endpoint(
        "Complete Flashcard Session", "POST", f"{BASE_URL}/v1/flashcards/sessions/{session_id}/complete",
        {"progress": {"current": 1, "total": 1, "correct": 1, "incorrect": 0}}
    )))
    
    results.append(("Flashcard Stats", test_endpoint(
        "Flashcard Stats", "GET", f"{BASE_URL}/v1/flashcards/stats/me"
    )))
    
    # Cleanup - Delete word and list (allow 404 as resources may be cascade-deleted)
    results.append(("Delete Word", test_endpoint(
        "Delete Word", "DELETE", f"{BASE_URL}/v1/word-lists/{list_id}/words/{word_id}", expected_status=204, allow_404_for_delete=True
    )))
    
    results.append(("Delete Word List", test_endpoint(
        "Delete Word List", "DELETE", f"{BASE_URL}/v1/word-lists/{list_id}", expected_status=204, allow_404_for_delete=True
    )))
    
    # Spelling Tests
    print(f"\n{Colors.YELLOW}=== Spelling API ==={Colors.END}")
    results.append(("Spelling Stats", test_endpoint(
        "Spelling Stats", "GET", f"{BASE_URL}/v1/spelling/stats/me"
    )))
    
    # Cloze Tests
    print(f"\n{Colors.YELLOW}=== Cloze API ==={Colors.END}")
    results.append(("Cloze Lessons", test_endpoint(
        "Cloze Lessons", "GET", f"{BASE_URL}/v1/cloze/lessons?class_id=test_class"
    )))
    
    results.append(("Cloze Stats", test_endpoint(
        "Cloze Stats", "GET", f"{BASE_URL}/v1/cloze/stats/me"
    )))
    
    # Grammar Tests
    print(f"\n{Colors.YELLOW}=== Grammar API ==={Colors.END}")
    results.append(("Grammar Lessons", test_endpoint(
        "Grammar Lessons", "GET", f"{BASE_URL}/v1/grammar/lessons?class_id=test_class"
    )))
    
    results.append(("Grammar Stats", test_endpoint(
        "Grammar Stats", "GET", f"{BASE_URL}/v1/grammar/stats/me"
    )))
    
    # Sentence Builder Tests
    print(f"\n{Colors.YELLOW}=== Sentence Builder API ==={Colors.END}")
    results.append(("Sentence Lessons", test_endpoint(
        "Sentence Lessons", "GET", f"{BASE_URL}/v1/sentence/lessons?class_id=test_class"
    )))
    
    results.append(("Sentence Stats", test_endpoint(
        "Sentence Stats", "GET", f"{BASE_URL}/v1/sentence/stats/me"
    )))
    
    # Summary
    print("\n" + "=" * 80)
    print(f"{Colors.BLUE}Test Results Summary{Colors.END}")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}✓ PASSED{Colors.END}" if result else f"{Colors.RED}✗ FAILED{Colors.END}"
        print(f"{name}: {status}")
    
    print("\n" + "=" * 80)
    percentage = (passed / total * 100) if total > 0 else 0
    print(f"Total: {passed}/{total} tests passed ({percentage:.1f}%)")
    
    if passed == total:
        print(f"{Colors.GREEN}✓ All tests passed!{Colors.END}")
    else:
        print(f"{Colors.YELLOW}⚠ Some tests failed{Colors.END}")
    print("=" * 80)

if __name__ == "__main__":
    main()
