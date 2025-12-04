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
    "family": [
        ("My _____ lives in London.", "family", "People related by blood or marriage"),
        ("We have a large _____.", "family", "Group of related people")
    ],
    "friend": [
        ("She is my best _____.", "friend", "Person you know well and like"),
        ("I met a new _____ at school.", "friend", "Someone you enjoy spending time with")
    ],
    "home": [
        ("I go _____ after work.", "home", "Place where someone lives"),
        ("Their _____ is very beautiful.", "home", "Dwelling place")
    ],
    "work": [
        ("I _____ in an office.", "work", "Have a job"),
        ("This _____ is very important.", "work", "Activity to achieve a purpose")
    ],
    "time": [
        ("What _____ is it?", "time", "Measurement in hours/minutes"),
        ("I need more _____ to finish.", "time", "Duration available")
    ],
    "water": [
        ("Can I have some _____?", "water", "Clear liquid essential for life"),
        ("The _____ is too cold to swim.", "water", "Liquid form of H2O")
    ],
    "food": [
        ("I need to buy _____ for dinner.", "food", "Substance eaten for nutrition"),
        ("This _____ tastes delicious.", "food", "Edible substance")
    ],
    "money": [
        ("I need more _____ to buy this.", "money", "Medium of exchange"),
        ("She saves _____ every month.", "money", "Currency or funds")
    ],
    "day": [
        ("Have a good _____!", "day", "24-hour period"),
        ("What a beautiful _____!", "day", "Daytime period")
    ],
    "year": [
        ("Next _____ I will travel.", "year", "365-day period"),
        ("This _____ has been amazing.", "year", "Calendar year")
    ],
    "people": [
        ("Many _____ came to the party.", "people", "Human beings"),
        ("These _____ are very friendly.", "people", "Group of individuals")
    ],
    "city": [
        ("New York is a big _____.", "city", "Large urban area"),
        ("I live in a small _____.", "city", "Municipal area")
    ],
    "country": [
        ("Israel is my favorite _____.", "country", "Sovereign nation"),
        ("Which _____ do you want to visit?", "country", "Geopolitical entity")
    ],
    "problem": [
        ("We need to solve this _____.", "problem", "Difficult situation"),
        ("The main _____ is communication.", "problem", "Issue or challenge")
    ],
    "question": [
        ("Do you have a _____?", "question", "Inquiry or query"),
        ("This _____ is very difficult.", "question", "Problem to be solved")
    ],
    "answer": [
        ("I know the _____!", "answer", "Response to a question"),
        ("Please give me an _____.", "answer", "Solution or reply")
    ],
    "child": [
        ("The _____ is playing outside.", "child", "Young human"),
        ("She has one _____.", "child", "Offspring")
    ],
    "parent": [
        ("My _____ lives nearby.", "parent", "Mother or father"),
        ("She is a single _____.", "parent", "Person raising children")
    ],
    "teacher": [
        ("The _____ explains the lesson.", "teacher", "Educator"),
        ("My _____ is very helpful.", "teacher", "Instructor")
    ],
    "student": [
        ("Every _____ has a book.", "student", "Learner"),
        ("He is a good _____.", "student", "Person studying")
    ],
    "job": [
        ("I need a new _____.", "job", "Employment position"),
        ("What is your _____?", "job", "Occupation")
    ],
    "health": [
        ("Exercise is good for your _____.", "health", "Physical condition"),
        ("Her _____ is improving.", "health", "Well-being")
    ],
    "weather": [
        ("The _____ is beautiful today.", "weather", "Atmospheric conditions"),
        ("How's the _____?", "weather", "Current climate")
    ],
    "world": [
        ("We live in a big _____.", "world", "Planet Earth"),
        ("Travel around the _____.", "world", "Global sphere")
    ],
    "life": [
        ("Enjoy your _____!", "life", "Existence"),
        ("This is the best _____ ever!", "life", "Personal experience")
    ],
    "understand": [
        ("Do you _____ the question?", "understand", "Comprehend meaning"),
        ("I don't _____ this lesson.", "understand", "Grasp information")
    ],
    "important": [
        ("This is very _____.", "important", "Having great significance"),
        ("Sleep is _____ for health.", "important", "Crucial or essential")
    ]
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
    generic_used = 0
    
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
    
    # Priority 3: Fill remaining slots with generic templates
    while len(out) < limit:
        template = random.choice(GENERIC_TEMPLATES)
        sentence_template, blank_position, concept, explanation_template = template
        
        # Replace blank with a random word
        sentence = sentence_template.replace("_____",
                                             random.choice(["apple", "dog", "run", "big", "happy"]))
        
        # Create options
        options = _build_options_for_target(random.choice(["apple", "dog", "run", "big", "happy"]))
        
        out.append({
            "id": str(uuid.uuid4()),
            "sentence": sentence,
            "options": options,
            "correct_answer": random.choice(options),
            "difficulty": _assess_difficulty(random.choice(options)),
            "source_mistake": "generic_template",
            "explanation": explanation_template,
            "hint": "Choose the word that best completes the sentence.",
            "concept": concept
        })
        generic_used += 1
    
    if generic_used > 0:
        logger.info(f"Generated {generic_used} fallback fill_blank items")
    
    return out[:limit]
