# src/ai/generators/fill_blank_generator.py
"""
Fill-in-the-blank exercise generator.

Generates pedagogically sound cloze-style exercises using:
1. Clean template sentences for common vocabulary
2. Mistake-based sentences when available
3. Never uses raw transcript noise

Each exercise includes:
- A natural English sentence with a blank
- Multiple choice options (4 choices)
- The correct answer
- Difficulty rating
- Explanation and hints
"""

from __future__ import annotations
import uuid
import random
import logging
from typing import List, Dict, Any, Set, Tuple

from .shared_utils import _build_options_for_target, _assess_difficulty

logger = logging.getLogger(__name__)

# Seed for reproducibility
random.seed(42)

# =============================================================================
# CLEAN TEMPLATE SENTENCES FOR VOCABULARY
# Each word has multiple natural English sentences
# =============================================================================
VOCABULARY_TEMPLATES: Dict[str, List[Tuple[str, str, str]]] = {
    # (sentence_with_blank, correct_answer, explanation)
    "open": [
        ("Please _____ the door.", "open", "Use 'open' to describe making something accessible."),
        ("Can you _____ the window? It's hot in here.", "open", "'Open' means to make something not closed."),
        ("I need to _____ my email.", "open", "We 'open' applications or messages to view them."),
    ],
    "camera": [
        ("I bought a new _____ for my trip.", "camera", "A 'camera' is a device for taking photos."),
        ("Please turn on your _____ for the video call.", "camera", "A 'camera' captures video or images."),
        ("The _____ on my phone takes great pictures.", "camera", "Phones have built-in cameras for photography."),
    ],
    "please": [
        ("Could you help me, _____?", "please", "'Please' is used to make polite requests."),
        ("_____ pass me the salt.", "Please", "Start requests with 'please' to be polite."),
        ("May I have some water, _____?", "please", "Add 'please' at the end for politeness."),
    ],
    "name": [
        ("What is your _____?", "name", "A 'name' is what someone is called."),
        ("Please write your _____ on the paper.", "name", "Your 'name' identifies who you are."),
        ("I forgot the _____ of that movie.", "name", "A 'name' is a title or label for something."),
    ],
    "fine": [
        ("How are you? I'm _____.", "fine", "'Fine' means good or okay."),
        ("The weather is _____ today.", "fine", "'Fine' can describe pleasant conditions."),
        ("Don't worry, everything will be _____.", "fine", "'Fine' means satisfactory or acceptable."),
    ],
    "great": [
        ("That's a _____ idea!", "great", "'Great' means excellent or very good."),
        ("We had a _____ time at the party.", "great", "'Great' describes something wonderful."),
        ("You did a _____ job on your homework.", "great", "'Great' is used to praise good work."),
    ],
    "amazing": [
        ("The view from the mountain was _____.", "amazing", "'Amazing' means extremely impressive."),
        ("She is an _____ singer.", "amazing", "'Amazing' describes exceptional talent."),
        ("That magic trick was _____!", "amazing", "'Amazing' expresses wonder or surprise."),
    ],
    "think": [
        ("I _____ this is the right answer.", "think", "'Think' means to believe or have an opinion."),
        ("What do you _____ about this book?", "think", "'Think' is used to ask for opinions."),
        ("Let me _____ about it for a moment.", "think", "'Think' means to consider something."),
    ],
    "know": [
        ("Do you _____ the answer?", "know", "'Know' means to have information."),
        ("I _____ how to swim.", "know", "'Know' indicates having a skill or knowledge."),
        ("She doesn't _____ where the library is.", "know", "'Know' means to be aware of something."),
    ],
    "morning": [
        ("I wake up early in the _____.", "morning", "The 'morning' is the early part of the day."),
        ("Good _____! How did you sleep?", "morning", "We greet people with 'Good morning'."),
        ("I have a meeting tomorrow _____.", "morning", "'Morning' refers to the time before noon."),
    ],
    "start": [
        ("Let's _____ the lesson now.", "start", "'Start' means to begin something."),
        ("What time does the movie _____?", "start", "'Start' indicates when something begins."),
        ("I want to _____ learning a new language.", "start", "'Start' means to commence an activity."),
    ],
    "close": [
        ("Please _____ the door when you leave.", "close", "'Close' means to shut something."),
        ("The store will _____ at 9 PM.", "close", "'Close' can mean to stop operating."),
        ("Can you _____ the window? It's cold.", "close", "'Close' is the opposite of 'open'."),
    ],
    "already": [
        ("I have _____ finished my homework.", "already", "'Already' means before now or sooner than expected."),
        ("She has _____ eaten breakfast.", "already", "'Already' indicates completion before a certain time."),
        ("They _____ know the answer.", "already", "'Already' emphasizes something happened earlier."),
    ],
    "letter": [
        ("I wrote a _____ to my grandmother.", "letter", "A 'letter' is a written message."),
        ("The alphabet has 26 _____s.", "letter", "A 'letter' is a character in the alphabet."),
        ("Please mail this _____ for me.", "letter", "A 'letter' is sent through the post."),
    ],
    "book": [
        ("I'm reading an interesting _____.", "book", "A 'book' is a written work with pages."),
        ("Can I borrow your _____?", "book", "A 'book' contains stories or information."),
        ("The _____ is on the table.", "book", "A 'book' is something you read."),
    ],
    "eat": [
        ("I _____ breakfast every morning.", "eat", "'Eat' means to consume food."),
        ("What do you want to _____ for dinner?", "eat", "'Eat' is the action of having a meal."),
        ("The children _____ lunch at school.", "eat", "'Eat' means to take in food."),
    ],
    "go": [
        ("I _____ to school every day.", "go", "'Go' means to move or travel somewhere."),
        ("Let's _____ to the park.", "go", "'Go' indicates movement to a place."),
        ("Where do you want to _____?", "go", "'Go' is used for traveling or moving."),
    ],
    "have": [
        ("I _____ two brothers.", "have", "'Have' indicates possession."),
        ("Do you _____ any questions?", "have", "'Have' is used to ask about possession."),
        ("We _____ a big house.", "have", "'Have' means to own or possess."),
    ],
}

# Fallback templates for words not in the vocabulary list
GENERIC_TEMPLATES: List[Tuple[str, str, str, str]] = [
    # (sentence_template, blank_position, concept, explanation_template)
    ("I like to _____ every day.", "verb", "verb_usage", "This verb describes a daily action."),
    ("The _____ is very beautiful.", "noun", "noun_usage", "This noun describes something you can see."),
    ("She is very _____.", "adjective", "adjective_usage", "This adjective describes a quality."),
    ("We went to the _____ yesterday.", "noun", "noun_usage", "This noun is a place you can visit."),
    ("He _____ to work every morning.", "verb", "verb_usage", "This verb describes regular movement."),
]


def _get_vocab_from_input(
    mistakes: List[Dict[str, Any]],
    transcript: str
) -> Set[str]:
    """Extract vocabulary words from mistakes and transcript."""
    vocab: Set[str] = set()
    
    # From mistakes
    for m in (mistakes or []):
        correct = m.get("correct") or m.get("corrected") or ""
        if correct and correct.isalpha():
            vocab.add(correct.lower())
    
    # Check which template words appear in transcript
    if transcript:
        transcript_lower = transcript.lower()
        for word in VOCABULARY_TEMPLATES.keys():
            if word in transcript_lower:
                vocab.add(word)
    
    return vocab


def generate_fill_blank(
    mistakes: List[Dict[str, Any]],
    transcript: str,
    *,
    limit: int = 8
) -> List[Dict[str, Any]]:
    """
    Generate fill-in-the-blank exercises using clean template sentences.
    
    Args:
        mistakes: List of mistake dictionaries (used to identify target vocabulary)
        transcript: Full transcript text (used to identify relevant vocabulary)
        limit: Maximum number of exercises to generate (default: 8)
    
    Returns:
        List of exercise dictionaries with natural English sentences.
    """
    out: List[Dict[str, Any]] = []
    used_words: Set[str] = set()
    
    # Get vocabulary from input
    input_vocab = _get_vocab_from_input(mistakes, transcript)
    
    # Priority 1: Generate from vocabulary that appears in input
    for word in input_vocab:
        if len(out) >= limit:
            break
        if word in used_words:
            continue
        if word not in VOCABULARY_TEMPLATES:
            continue
        
        templates = VOCABULARY_TEMPLATES[word]
        template = random.choice(templates)
        sentence, correct, explanation = template
        
        used_words.add(word)
        options = _build_options_for_target(correct)
        
        out.append({
            "id": str(uuid.uuid4()),
            "sentence": sentence,
            "options": options,
            "correct_answer": correct,
            "difficulty": _assess_difficulty(correct),
            "source_mistake": "vocabulary_template",
            "explanation": explanation,
            "hint": "Choose the word that best completes the sentence.",
            "concept": "vocabulary"
        })
    
    # Priority 2: Fill remaining slots with other common vocabulary
    remaining_words = [w for w in VOCABULARY_TEMPLATES.keys() if w not in used_words]
    random.shuffle(remaining_words)
    
    for word in remaining_words:
        if len(out) >= limit:
            break
        
        templates = VOCABULARY_TEMPLATES[word]
        template = random.choice(templates)
        sentence, correct, explanation = template
        
        used_words.add(word)
        options = _build_options_for_target(correct)
        
        out.append({
            "id": str(uuid.uuid4()),
            "sentence": sentence,
            "options": options,
            "correct_answer": correct,
            "difficulty": _assess_difficulty(correct),
            "source_mistake": "vocabulary_template",
            "explanation": explanation,
            "hint": "Choose the word that best completes the sentence.",
            "concept": "vocabulary"
        })
    
    return out[:limit]
