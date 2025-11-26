"""Production-ready exercise generators with translations and mistake focus."""

from __future__ import annotations
import logging
import uuid
import random
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Translation support (default English → Hebrew, code "he")
try:
    from deep_translator import GoogleTranslator
    TRANSLATE_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    GoogleTranslator = None
    TRANSLATE_AVAILABLE = False


def _build_translator(target_lang: str = 'he') -> Optional[GoogleTranslator]:
    if not TRANSLATE_AVAILABLE or not GoogleTranslator:
        return None
    try:
        return GoogleTranslator(source='en', target=target_lang)
    except Exception as exc:  # pragma: no cover - network failure
        logger.warning("Translator init failed (%s). Falling back to empty translations", exc)
        return None


def _translate(text: str, translator: Optional[GoogleTranslator]) -> str:
    if not text or not translator:
        return ''
    try:
        return translator.translate(text)
    except Exception as exc:  # pragma: no cover
        logger.warning("Translation failed for '%s': %s", text, exc)
        return ''


@dataclass
class Flashcard:
    id: str
    word: str
    translation: str
    example_sentence: Optional[str] = None
    notes: Optional[str] = None
    category: Optional[str] = None
    difficulty: str = "medium"
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "word": self.word,
            "translation": self.translation,
            "example_sentence": self.example_sentence,
            "notes": self.notes,
            "category": self.category,
            "difficulty": self.difficulty,
            "metadata": self.metadata,
        }


@dataclass
class ClozeItem:
    id: str
    sentence: str
    options: List[str]
    correct_answer: str
    explanation: str
    difficulty: str = "medium"
    topic: Optional[str] = None
    student_mistake: Optional[str] = None
    focus: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        parts = self.sentence.split('_____')
        return {
            "id": self.id,
            "sentence": self.sentence,
            "text_parts": parts if len(parts) == 2 else [self.sentence, ""],
            "options": [self.options],
            "correct_answers": [self.correct_answer],
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
            "difficulty": self.difficulty,
            "topic": self.topic,
            "student_mistake": self.student_mistake,
            "focus": self.focus,
            "metadata": self.metadata,
        }


@dataclass
class GrammarQuestion:
    id: str
    prompt: str
    options: List[str]
    correct_index: int
    explanation: str
    category: Optional[str] = None
    difficulty: str = "medium"
    student_mistake: Optional[str] = None
    focus: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "options": self.options,
            "correctIndex": self.correct_index,  # camelCase for frontend compatibility
            "correct_answer": self.options[self.correct_index],
            "explanation": self.explanation,
            "category": self.category,
            "lesson": self.category,  # Use category as lesson for now
            "difficulty": self.difficulty,
            "student_mistake": self.student_mistake,
            "focus": self.focus,
            "metadata": self.metadata,
        }


@dataclass
class SentenceItem:
    id: str
    english_sentence: str
    sentence_tokens: List[str]
    accepted_sequences: List[List[str]]
    distractors: List[str]
    translation: Optional[str] = None
    hint: Optional[str] = None
    difficulty: str = "medium"
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "english": self.english_sentence,  # Frontend expects 'english'
            "english_sentence": self.english_sentence,  # Keep for backward compat
            "tokens": self.sentence_tokens,  # Frontend expects 'tokens'
            "sentence_tokens": self.sentence_tokens,  # Keep for backward compat
            "accepted": self.accepted_sequences,  # Frontend expects 'accepted'
            "accepted_sequences": self.accepted_sequences,  # Keep for backward compat
            "distractors": self.distractors,
            "translation": self.translation,
            "hint": self.hint,
            "difficulty": self.difficulty,
            "topic": None,  # Can be set by backend if needed
            "lesson": None,  # Can be set by backend if needed
            "metadata": self.metadata,
        }


def _normalize_sentence(text: str) -> str:
    text = re.sub(r"([.!?,;:])\1+", r"\1", text)
    text = re.sub(r"\s+([.!?,;:])", r"\1", text)
    text = re.sub(r"([.!?,;:])([A-Za-z])", r"\1 \2", text)
    return text.strip()


def _extract_sentences(transcript: str, min_words: int = 5, max_words: int = 20) -> List[str]:
    sentences = re.split(r"[.!?]+", transcript)
    clean = []
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        sent = re.sub(r"^(Teacher|Student):\s*", "", sent, flags=re.IGNORECASE)
        sent = _normalize_sentence(sent)
        words = sent.split()
        if min_words <= len(words) <= max_words and any(w.lower() in {"i","you","he","she","we","they"} for w in words):
            clean.append(sent)
    return clean


def generate_flashcards(
    vocabulary: List[Dict[str, str]],
    transcript: str,
    *,
    limit: int = 12,
    target_lang: str = 'he'
) -> List[Dict[str, Any]]:
    translator = _build_translator(target_lang)
    cards: List[Flashcard] = []
    sentences = _extract_sentences(transcript)

    for vocab_item in vocabulary[:limit]:
        word = (vocab_item.get("word") or "").strip()
        if not word:
            continue
        # Skip items that look like full sentences (more than 5 words)
        if len(word.split()) > 5:
            logger.debug("Skipping too-long flashcard word: %s", word[:50])
            continue
        # Always translate using our configured translator so the language is consistent (Hebrew).
        translation = _translate(word, translator)
        # Use context from vocab item first, then search transcript
        example = vocab_item.get("context") or vocab_item.get("example_sentence")
        if not example:
            example = next((s for s in sentences if word.lower() in s.lower()), None)
        cards.append(Flashcard(
            id=str(uuid.uuid4()),
            word=word,
            translation=translation,
            example_sentence=example,
            notes=vocab_item.get("notes"),
            category=vocab_item.get("category", "general"),
            difficulty="beginner" if len(word.split()) == 1 and len(word) < 8 else "intermediate",
            metadata={"source": "vocabulary"},
        ))
    return [c.to_dict() for c in cards]


def _diff_word(correct_words: List[str], incorrect_words: List[str]) -> Optional[str]:
    for idx, word in enumerate(correct_words):
        if idx >= len(incorrect_words) or word.lower() != incorrect_words[idx].lower():
            return word.strip('.,;:!?')
    return None


def _distractors(word: str, mistake_type: str, incorrect_words: List[str]) -> List[str]:
    if not word:
        return []
    variants = []
    base = word.rstrip('seding')
    if 'verb_tense' in mistake_type:
        variants = [base + "ing", base + "ed", base + "s"]
    elif 'subject_verb_agreement' in mistake_type:
        variants = [word + "s", base, word + "ed"]
    elif 'article' in mistake_type:
        variants = ['a', 'an', 'the']
    elif 'plural' in mistake_type:
        variants = [word + 's', word + 'es', base]
    elif 'preposition' in mistake_type:
        variants = ['to', 'at', 'in', 'on', 'for', 'with']
    else:
        variants = [w.strip('.,;:!?') for w in incorrect_words]
    uniq = []
    seen = set()
    for v in variants:
        if not v or v.lower() == word.lower() or v.lower() in seen:
            continue
        uniq.append(v)
        seen.add(v.lower())
        if len(uniq) == 3:
            break
    return uniq


def generate_cloze(
    mistakes: List[Dict[str, str]],
    transcript: str,
    *,
    limit: int = 8
) -> List[Dict[str, Any]]:
    items: List[ClozeItem] = []
    _ = _extract_sentences(transcript)  # Currently not used but kept for context
    for mistake in mistakes[:limit]:
        incorrect = (mistake.get("incorrect") or "").strip()
        correct = (mistake.get("correct") or "").strip()
        if not correct:
            continue
        correct_words = correct.split()
        incorrect_words = incorrect.split()
        blank = _diff_word(correct_words, incorrect_words) or (correct_words[0] if correct_words else None)
        if not blank:
            continue
        sentence = correct.replace(blank, "_____", 1)
        distractors = _distractors(blank, mistake.get("type", "grammar_general"), incorrect_words)
        options = [blank] + distractors
        while len(options) < 4:
            options.append(blank.lower() if blank.lower() != blank else blank.upper())
        random.shuffle(options)
        explanation = mistake.get("rule") or "Use the grammatically correct form."
        items.append(ClozeItem(
            id=str(uuid.uuid4()),
            sentence=sentence,
            options=options[:4],
            correct_answer=blank,
            explanation=explanation,
            difficulty="beginner" if len(correct_words) < 8 else "intermediate",
            topic=mistake.get("type"),
            student_mistake=incorrect,
            focus=mistake.get("type"),
            metadata={"source": "mistake"},
        ))
    return [c.to_dict() for c in items]


def generate_grammar(
    mistakes: List[Dict[str, str]],
    *,
    limit: int = 8
) -> List[Dict[str, Any]]:
    questions: List[GrammarQuestion] = []
    for mistake in mistakes[:limit]:
        incorrect = (mistake.get("incorrect") or "").strip()
        correct = (mistake.get("correct") or "").strip()
        if not correct:
            continue
        correct_words = correct.split()
        incorrect_words = incorrect.split()
        blank_word = _diff_word(correct_words, incorrect_words) or (correct_words[0] if correct_words else None)
        if not blank_word:
            continue
        idx = correct_words.index(blank_word) if blank_word in correct_words else 0
        prompt_words = correct_words.copy()
        prompt_words[idx] = '_____'
        prompt = ' '.join(prompt_words)
        options = _distractors(blank_word, mistake.get("type", "grammar_general"), incorrect_words)
        options = [blank_word] + options
        while len(options) < 4:
            options.append(blank_word + "s" if not blank_word.endswith("s") else blank_word[:-1])
        random.shuffle(options)
        correct_index = options.index(blank_word)
        rule = mistake.get("rule") or "This is the correct grammatical form."
        explanation = f"Use '{blank_word}' because {rule.lower()}"
        if incorrect:
            explanation += f" (student said '{incorrect}')."
        questions.append(GrammarQuestion(
            id=str(uuid.uuid4()),
            prompt=prompt,
            options=options[:4],
            correct_index=correct_index,
            explanation=explanation,
            category=mistake.get("type"),
            difficulty="beginner" if len(correct_words) < 8 else "intermediate",
            student_mistake=incorrect,
            focus=mistake.get("type"),
            metadata={"source": "mistake"},
        ))
    return [q.to_dict() for q in questions]


def generate_sentence_items(
    sentences: List[Dict[str, str]],
    *,
    limit: int = 8,
    target_lang: str = 'he'
) -> List[Dict[str, Any]]:
    translator = _build_translator(target_lang)
    items: List[SentenceItem] = []
    for sent in sentences[:limit]:
        sentence = (sent.get("sentence") or "").strip()
        if not sentence:
            continue
        sentence = _normalize_sentence(sentence)
        if not sentence.endswith(('.', '!', '?')):
            sentence += '.'
        words = sentence.split()
        tokens = [w if idx == len(words) - 1 else w.strip('.,;:!?') for idx, w in enumerate(words)]
        distractors = [w for w in ["the", "a", "is", "are", "was", "were"] if w not in {t.lower() for t in tokens}][:3]
        translation = _translate(sentence, translator)
        diff = 'beginner' if len(tokens) <= 5 else 'intermediate' if len(tokens) <= 8 else 'advanced'
        items.append(SentenceItem(
            id=str(uuid.uuid4()),
            english_sentence=sentence,
            sentence_tokens=tokens,
            accepted_sequences=[tokens],
            distractors=distractors,
            translation=translation,
            hint=sent.get("hint"),
            difficulty=diff,
            metadata={"source": "sentence"},
        ))
    return [s.to_dict() for s in items]
