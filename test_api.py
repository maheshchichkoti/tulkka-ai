"""Quick test script to verify API is working"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{BASE_URL}/v1/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_process_transcript():
    """Test transcript processing"""
    print("\n=== Testing Transcript Processing ===")
    payload = {
        "transcript": "Today we learned about present perfect tense. The student said 'I have went' but the correct form is 'I have gone'. We practiced with sentences like 'I have visited Paris' and 'She has finished her homework'.",
        "lesson_number": 1
    }
    response = requests.post(f"{BASE_URL}/api/v1/process", json=payload)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Exercises generated:")
        print(f"  - Flashcards: {len(data.get('exercises', {}).get('flashcards', []))}")
        print(f"  - Cloze: {len(data.get('exercises', {}).get('cloze', []))}")
        print(f"  - Grammar: {len(data.get('exercises', {}).get('grammar', []))}")
        print(f"  - Sentence: {len(data.get('exercises', {}).get('sentence', []))}")
    else:
        print(f"Error: {response.text}")
    return response.status_code == 200

def test_docs():
    """Test API documentation"""
    print("\n=== Testing API Documentation ===")
    response = requests.get(f"{BASE_URL}/docs")
    print(f"Status: {response.status_code}")
    print(f"Docs available at: {BASE_URL}/docs")
    return response.status_code == 200

if __name__ == "__main__":
    print("=" * 60)
    print("Tulkka AI - API Test Suite")
    print("=" * 60)
    
    results = []
    results.append(("Health Check", test_health()))
    results.append(("API Documentation", test_docs()))
    results.append(("Process Transcript", test_process_transcript()))
    
    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name}: {status}")
    
    all_passed = all(result[1] for result in results)
    print("\n" + ("=" * 60))
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
    print("=" * 60)
