"""High-quality flashcard generator (rule-based).

For each vocab item we ensure:
- Correct Hebrew translations for tricky words via overrides
- A clean, pedagogically sound example sentence
- Never uses transcript noise or single-word sentences
"""

from __future__ import annotations
import uuid
import re
from typing import List, Dict, Any, Optional
from .shared_utils import _translator, _tr, _assess_difficulty, _clean_sentence_for_example


TRANSLATION_OVERRIDES = {
    # Sense-correct overrides for common polysemous words
    "fine": "בסדר",   # "I'm fine" → בסדר
    "great": "מצוין",  # "great/excellent" → מצוין
    "amazing": "מדהים",
    "open": "לִפְתוֹחַ",
    "close": "לִסְגוֹר",
    "camera": "מַצלֵמָה",
    "please": "בבקשה",
    "name": "שֵׁם",
    "think": "לַחשׁוֹב",
    "know": "לָדַעַת",
    "morning": "בֹּקֶר",
    "start": "לְהַתְחִיל",
    "book": "סֵפֶר",
    "letter": "מִכְתָּב",
    "eat": "לֶאֱכוֹל",
    "go": "לָלֶכֶת",
    "have": "יֵשׁ לִי",
}

# Clean example sentences for common vocabulary (pedagogically sound)
EXAMPLE_SENTENCES: Dict[str, str] = {
    "open": "Can you open the window, please?",
    "close": "Please close the door when you leave.",
    "camera": "I need to turn on my camera for the video call.",
    "please": "Could you help me with this, please?",
    "name": "What is your name?",
    "fine": "How are you? I'm fine, thank you.",
    "great": "That's a great idea!",
    "amazing": "The view from here is amazing.",
    "think": "I think this is the right answer.",
    "know": "Do you know where the library is?",
    "morning": "I wake up early in the morning.",
    "start": "Let's start the lesson now.",
    "book": "I'm reading an interesting book.",
    "letter": "I wrote a letter to my friend.",
    "eat": "I eat breakfast every morning.",
    "go": "I go to school every day.",
    "have": "I have two brothers and one sister.",
    "already": "I have already finished my homework.",
    "hello": "Hello! How are you today?",
    "goodbye": "Goodbye! See you tomorrow.",
    "thank": "Thank you for your help.",
    "sorry": "I'm sorry for being late.",
    "yes": "Yes, I understand.",
    "no": "No, thank you.",
    "today": "What are you doing today?",
    "tomorrow": "I have a meeting tomorrow.",
    "yesterday": "I went to the park yesterday.",
    "now": "I'm busy right now.",
    "here": "Please come here.",
    "there": "The book is over there.",
    "good": "This is a good book.",
    "bad": "The weather is bad today.",
    "big": "We live in a big house.",
    "small": "I have a small dog.",
    "new": "I bought a new phone.",
    "old": "This is an old building.",
    "happy": "I'm happy to see you.",
    "sad": "She looks sad today.",
    "like": "I like to read books.",
    "want": "I want to learn English.",
    "need": "I need your help.",
    "see": "I can see the mountains from here.",
    "hear": "Can you hear me?",
    "say": "What did you say?",
    "tell": "Please tell me the story.",
    "ask": "Can I ask you a question?",
    "answer": "Do you know the answer?",
    "learn": "I want to learn a new language.",
    "teach": "She teaches English at school.",
    "read": "I read a book every week.",
    "write": "Please write your name here.",
    "speak": "Do you speak English?",
    "listen": "Please listen carefully.",
    "work": "I work in an office.",
    "play": "The children play in the park.",
    "live": "I live in a small town.",
    "come": "Please come to my party.",
    "make": "I want to make a cake.",
    "take": "Please take a seat.",
    "give": "Can you give me that book?",
    "find": "I can't find my keys.",
    "use": "How do you use this machine?",
    "try": "I want to try something new.",
    "help": "Can you help me, please?",
    "call": "I will call you tomorrow.",
    "walk": "I walk to school every day.",
    "run": "He runs very fast.",
    "sit": "Please sit down.",
    "stand": "Please stand up.",
    "wait": "Please wait here.",
    "look": "Look at this picture.",
    "watch": "I like to watch movies.",
    "time": "What time is it?",
    "day": "Have a nice day!",
    "night": "Good night! Sleep well.",
    "week": "I exercise three times a week.",
    "month": "My birthday is next month.",
    "year": "Happy New Year!",
    "water": "Can I have some water, please?",
    "food": "The food here is delicious.",
    "house": "We live in a big house.",
    "school": "I go to school every day.",
    "family": "I love my family.",
    "friend": "She is my best friend.",
    "mother": "My mother is a teacher.",
    "father": "My father works in a hospital.",
}

# Words to filter out from transcript
NOISE_WORDS = {"okay", "ok", "um", "uh", "hmm", "yeah", "right", "so", "well", "like"}
NOISE_NAMES = {"khadija", "basmala", "emam", "mahaba", "philip"}


def _is_clean_sentence(sentence: str) -> bool:
    """Check if a sentence is clean and pedagogically appropriate."""
    if not sentence:
        return False
    
    words = sentence.split()
    
    # Must have at least 4 words
    if len(words) < 4:
        return False
    
    # Check for noise patterns
    lower = sentence.lower()
    
    # Skip sentences with names
    if any(name in lower for name in NOISE_NAMES):
        return False
    
    # Skip sentences starting with filler words
    first_word = words[0].lower().rstrip(".,!?")
    if first_word in NOISE_WORDS:
        return False
    
    # Skip sentences with ellipsis or multiple punctuation
    if "..." in sentence or "…" in sentence:
        return False
    if sentence.count("?") > 1 or sentence.count("!") > 1:
        return False
    
    # Skip incomplete sentences (ending with comma or no punctuation)
    if sentence.rstrip()[-1] not in ".!?":
        return False
    
    return True


def _get_example_sentence(word: str, transcript: str) -> str:
    """Get a clean example sentence for a word.
    
    Priority:
    1. Pre-defined clean example sentences
    2. Clean sentence from transcript (if passes quality check)
    3. Generated fallback sentence
    """
    word_lower = word.lower()
    
    # Priority 1: Use pre-defined clean examples
    if word_lower in EXAMPLE_SENTENCES:
        return EXAMPLE_SENTENCES[word_lower]
    
    # Priority 2: Try to find a clean sentence in transcript
    if transcript:
        cleaned = re.sub(r"[A-Za-z][A-Za-z ]{0,40}:\s*", "", transcript)
        parts = re.split(r"(?<=[.!?])\s+", cleaned)
        
        for p in parts:
            sentence = _clean_sentence_for_example(p.strip())
            if word_lower in sentence.lower() and _is_clean_sentence(sentence):
                return sentence
    
    # Priority 3: Generate a simple fallback
    return f"I use the word '{word}' in my English class."


def generate_flashcards(vocab: List[Dict[str, Any]], transcript: str, *, limit: int = 8) -> List[Dict[str, Any]]:
    """
    Generate flashcard exercises from vocabulary list.
    
    Args:
        vocab: List of vocabulary items (dicts with 'word', 'text', etc.)
        transcript: Full transcript for context extraction
        limit: Maximum number of flashcards to generate
    
    Returns:
        List of flashcard dictionaries with word, translation, example_sentence, etc.
    """
    t = _translator("he")
    out: List[Dict[str, Any]] = []
    cnt = 0

    for v in (vocab or []):
        if cnt >= limit:
            break

        if isinstance(v, dict):
            word = (v.get("word") or v.get("text") or "").strip()
            provided_example = v.get("example_sentence") or v.get("context") or ""
            source = v.get("category") or "content_word"
        else:
            word = str(v).strip()
            provided_example = ""
            source = "content_word"

        if not word:
            continue

        # Get a clean example sentence (prioritizes pre-defined over transcript)
        example_clean = _get_example_sentence(word, transcript)
        
        # If provided example is clean, prefer it
        if provided_example and _is_clean_sentence(provided_example):
            example_clean = _clean_sentence_for_example(provided_example)

        # Sense-correct translation with overrides, then translator fallback
        translation = TRANSLATION_OVERRIDES.get(word.lower()) or _tr(word, t)
        difficulty = _assess_difficulty(word)
        hint = f"Word from lesson ({source})"

        out.append({
            "id": str(uuid.uuid4()),
            "word": word,
            "translation": translation,
            "example_sentence": example_clean,
            "difficulty": difficulty,
            "source": source,
            "hint": hint,
        })
        cnt += 1

    return out
