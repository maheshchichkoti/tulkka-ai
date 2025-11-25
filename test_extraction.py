"""Test script to verify mistake extraction and exercise generation"""
from src.ai.lesson_processor import LessonProcessor

# Sample transcript from the task
transcript = """
Teacher: Today we will practice daily routines. What time do you wake up?
Student: I waking up at 7 AM.
Teacher: Good try! The correct sentence is I wake up at 7 AM.
Student: Then I brush my teeth and eat breakfast.
Teacher: Nice. What do you usually eat?
Student: I eats bread and egg.
Teacher: Careful! I eat bread and eggs.
"""

processor = LessonProcessor()
result = processor.process_lesson(transcript, lesson_number=1)

print("=== MISTAKES ===")
for m in result.get("mistakes", []):
    print(f"  - Incorrect: {m.get('incorrect')}")
    print(f"    Correct: {m.get('correct')}")
    print(f"    Type: {m.get('type')}")
    print()

print("=== CLOZE (Fill-in-blank) ===")
for c in result.get("cloze", []):
    print(f"  - Sentence: {c.get('sentence')}")
    print(f"    Options: {c.get('options')}")
    print(f"    Correct: {c.get('correct_answer')}")
    print()

print("=== GRAMMAR ===")
for g in result.get("grammar", []):
    print(f"  - Prompt: {g.get('prompt')}")
    print(f"    Options: {g.get('options')}")
    print(f"    Correct: {g.get('correct_answer')}")
    print()

print("=== FLASHCARDS ===")
for f in result.get("flashcards", [])[:5]:
    print(f"  - Word: {f.get('word')}")
    print(f"    Translation: {f.get('translation')}")
    print()

print("=== SENTENCE BUILDER ===")
for s in result.get("sentence", [])[:3]:
    print(f"  - Sentence: {s.get('english_sentence')}")
    print(f"    Tokens: {s.get('sentence_tokens')}")
    print()

print("=== COUNTS ===")
print(f"  Mistakes: {len(result.get('mistakes', []))}")
print(f"  Cloze: {len(result.get('cloze', []))}")
print(f"  Grammar: {len(result.get('grammar', []))}")
print(f"  Flashcards: {len(result.get('flashcards', []))}")
print(f"  Sentences: {len(result.get('sentence', []))}")
