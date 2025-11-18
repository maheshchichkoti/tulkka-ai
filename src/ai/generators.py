# src/ai/generators.py
"""
Heuristic generators for exercises. These are light-weight fallback generators that
produce usable content without an LLM. They are intentionally conservative.

Structures:
- Flashcard
- ClozeItem
- GrammarQuestion
- SentenceItem

Each generator accepts text (or paragraphs) and returns lists of items.
You can optionally pass an `llm_fn(paragraph, task)` callable to generate higher-quality content.
"""

from __future__ import annotations
import logging
import uuid
import random
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass

# Optional: Translation for fallback (default English → Hebrew)
try:
    from deep_translator import GoogleTranslator
    translator = GoogleTranslator(source='en', target='he')
    TRANSLATE_AVAILABLE = True
except ImportError:
    TRANSLATE_AVAILABLE = False
    translator = None

logger = logging.getLogger(__name__)

# Data models (simple dataclasses)
@dataclass
class Flashcard:
    id: str
    word: str
    translation: str
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'word': self.word,
            'translation': self.translation,
            'notes': self.notes,
            'metadata': self.metadata
        }

@dataclass
class ClozeItem:
    id: str
    topic: Optional[str]
    lesson: Optional[str]
    difficulty: str
    text_parts: List[str]  # surrounding text split by blanks
    options: List[List[str]]
    correct_answers: List[str]
    explanation: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'topic': self.topic,
            'lesson': self.lesson,
            'difficulty': self.difficulty,
            'text_parts': self.text_parts,
            'options': self.options,
            'correct_answers': self.correct_answers,
            'explanation': self.explanation,
            'metadata': self.metadata
        }

@dataclass
class GrammarQuestion:
    id: str
    category: Optional[str]
    difficulty: str
    prompt: str
    options: List[str]
    correct_index: int
    explanation: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'category': self.category,
            'difficulty': self.difficulty,
            'prompt': self.prompt,
            'options': self.options,
            'correct_index': self.correct_index,
            'explanation': self.explanation,
            'metadata': self.metadata
        }

@dataclass
class SentenceItem:
    id: str
    english_sentence: str
    translation: Optional[str]
    sentence_tokens: List[str]
    accepted_sequences: List[List[str]]
    distractors: List[str]
    hint: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'english_sentence': self.english_sentence,
            'translation': self.translation,
            'sentence_tokens': self.sentence_tokens,
            'accepted_sequences': self.accepted_sequences,
            'distractors': self.distractors,
            'hint': self.hint,
            'metadata': self.metadata
        }

# Helper: simple noun extraction (pick capitalized words or frequent content words)
def _pick_candidate_words(paragraph: str, limit: int = 10) -> List[str]:
    words = []
    tokens = paragraph.split()
    for t in tokens:
        clean = t.strip(".,;:()[]\"'").strip()
        if not clean:
            continue
        # heuristics: proper nouns (capitalized mid-sentence), or longer meaningful tokens
        if len(clean) > 6 or (clean[0].isupper() and not clean.isupper()):
            words.append(clean)
    # fallback: take top unique words
    if not words:
        seen = set()
        for t in tokens:
            w = t.strip(".,;:()[]\"'").lower()
            if len(w) > 5 and w not in seen:
                seen.add(w)
                words.append(w)
            if len(words) >= limit:
                break
    return words[:limit]

# -- GENERATORS ---

def generate_flashcards_from_text(
    paragraphs: List[str],
    *,
    limit: int = 20,
    llm_fn: Optional[Callable[[str, str], List[Dict[str, Any]]]] = None
) -> List[Flashcard]:
    """
    Generate flashcard candidates from paragraphs.
    If llm_fn provided, it is called as llm_fn(paragraph, "flashcards") and expected to return
    a list of dicts with {word, translation, notes}.
    Fallback heuristic picks candidate words and creates placeholders for translations.
    """
    cards: List[Flashcard] = []
    for p in paragraphs:
        if llm_fn:
            try:
                results = llm_fn(p, "flashcards")
                for r in results:
                    if len(cards) >= limit:
                        break
                    cards.append(Flashcard(id=str(uuid.uuid4()), word=r.get("word"), translation=r.get("translation",""), notes=r.get("notes")))
                if len(cards) >= limit:
                    break
            except Exception:
                logger.exception("LLM flashcard generation failed, falling back to heuristic")
        # heuristic
        candidates = _pick_candidate_words(p, limit=5)
        for w in candidates:
            if len(cards) >= limit:
                break
            # Try to translate if translator available
            translation = ""
            if TRANSLATE_AVAILABLE and translator:
                try:
                    translation = translator.translate(w)
                except Exception:
                    logger.warning(f"Translation failed for '{w}'")
            cards.append(Flashcard(id=str(uuid.uuid4()), word=w, translation=translation, notes="autogen"))
        if len(cards) >= limit:
            break
    return cards

def generate_cloze_from_text(
    paragraphs: List[str],
    *,
    max_items: int = 10,
    difficulty: str = "medium",
    llm_fn: Optional[Callable[[str, str], List[Dict[str, Any]]]] = None
) -> List[ClozeItem]:
    """
    Heuristic cloze generator: choose sentences and mask a content word to create options.
    Each ClozeItem.text_parts is [before, after] for a single-blank sentence.
    Options include the correct word and simple distractors.
    """
    items: List[ClozeItem] = []
    for p in paragraphs:
        # split into sentences
        sents = [s.strip() for s in p.split(".") if s.strip()]
        for s in sents:
            if len(items) >= max_items:
                break
            words = s.split()
            if len(words) < 6:
                continue
            # pick candidate index (prefer longer content words)
            idx_candidates = [i for i,w in enumerate(words) if len(w.strip(".,;:")) > 5]
            if not idx_candidates:
                idx = len(words)//2
            else:
                idx = random.choice(idx_candidates)
            correct = words[idx].strip(".,;:()\"'")
            before = " ".join(words[:idx]).strip()
            after = " ".join(words[idx+1:]).strip()
            # build distractors: small variations
            distractors = [correct]
            distractors += [correct[::-1][:len(correct)] for _ in range(2)]  # silly fallback distractors
            # ensure uniqueness
            options = list(dict.fromkeys(distractors))[:3]
            items.append(ClozeItem(
                id=str(uuid.uuid4()),
                topic=None,
                lesson=None,
                difficulty=difficulty,
                text_parts=[before, after],
                options=[options],
                correct_answers=[correct],
                explanation=None,
                metadata={"source": "heuristic"}
            ))
        if len(items) >= max_items:
            break
    return items

def generate_grammar_from_text(
    paragraphs: List[str],
    *,
    max_questions: int = 10,
    difficulty: str = "medium",
    llm_fn: Optional[Callable[[str, str], List[Dict[str, Any]]]] = None
) -> List[GrammarQuestion]:
    """
    Produce simple grammar multiple-choice questions by finding sentences and replacing verbs with blanks.
    Heuristic: find sentences with common auxiliaries and create choices.
    """
    questions: List[GrammarQuestion] = []
    auxiliaries = ["is", "are", "was", "were", "has", "have", "had", "will", "would", "can", "could", "should", "may"]
    for p in paragraphs:
        sents = [s.strip() for s in p.split(".") if s.strip()]
        for s in sents:
            if len(questions) >= max_questions:
                break
            tokens = s.split()
            for i,tok in enumerate(tokens):
                if tok.lower() in auxiliaries:
                    # make a blank at position i
                    prompt = " ".join(tokens[:i] + ["_____"] + tokens[i+1:])
                    opts = [tok, "did", "do", "does"]
                    correct_index = 0
                    questions.append(GrammarQuestion(
                        id=str(uuid.uuid4()),
                        category=None,
                        difficulty=difficulty,
                        prompt=prompt,
                        options=opts,
                        correct_index=correct_index,
                        explanation=None,
                        metadata={"source":"heuristic"}
                    ))
                    break
            if len(questions) >= max_questions:
                break
        if len(questions) >= max_questions:
            break
    return questions

def generate_sentence_items_from_text(
    paragraphs: List[str],
    *,
    max_items: int = 10,
    difficulty: str = "medium",
    llm_fn: Optional[Callable[[str, str], List[Dict[str, Any]]]] = None
) -> List[SentenceItem]:
    """
    Create sentence-builder items by taking short sentences and tokenizing them.
    accepted_sequences uses the canonical token order.
    """
    items: List[SentenceItem] = []
    for p in paragraphs:
        sents = [s.strip() for s in p.split(".") if s.strip()]
        for s in sents:
            if len(items) >= max_items:
                break
            tokens = [t.strip() for t in s.split() if t.strip()]
            if len(tokens) < 3 or len(tokens) > 25:
                continue
            items.append(SentenceItem(
                id=str(uuid.uuid4()),
                english_sentence=s + ".",
                translation=None,
                sentence_tokens=tokens,
                accepted_sequences=[tokens],
                distractors=[],
                hint=None,
                metadata={"source":"heuristic"}
            ))
        if len(items) >= max_items:
            break
    return items
