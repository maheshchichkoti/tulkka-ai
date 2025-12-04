# src/ai/generators/shared_utils.py
"""
Shared utilities for all rule-based generators.

Includes:
- Translation helper
- Difficulty scoring
- Sentence cleaning
- Morphology helpers
- Distractor generation
"""

from __future__ import annotations
import random
import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)
random.seed(1337)

# Optional translator with proper error handling
try:
    from deep_translator import GoogleTranslator

    _TRANSLATOR_AVAILABLE = True
except ImportError:
    GoogleTranslator = None  # type: ignore
    _TRANSLATOR_AVAILABLE = False


def _translator(target: str = "he"):
    """Create a translator instance for the target language."""
    if not _TRANSLATOR_AVAILABLE:
        return None
    lang = "iw" if target.lower() == "he" else target
    try:
        return GoogleTranslator(source="en", target=lang)
    except Exception as e:
        logger.warning("Translator init failed: %s", e)
        return None


def _tr(text: str, translator) -> str:
    """Translate text using the provided translator instance."""
    if not text or not translator:
        return ""
    try:
        result = translator.translate(text)
        return result if result else ""
    except Exception as e:
        logger.debug("Translation failed for '%s': %s", text[:20], e)
        return ""


COMMON_WORDS = {
    "open",
    "close",
    "name",
    "please",
    "camera",
    "hello",
    "thank",
    "fine",
    "great",
    "eat",
    "go",
    "have",
    "is",
    "are",
}


def _assess_difficulty(text: str) -> str:
    if not text:
        return "beginner"
    tokens = re.findall(r"[A-Za-z']+", text)
    if not tokens:
        return "beginner"
    if len(tokens) == 1:
        w = tokens[0].lower()
        if w in COMMON_WORDS or len(w) <= 4:
            return "beginner"
        if len(w) <= 7:
            return "intermediate"
        return "advanced"
    avg_len = sum(len(t) for t in tokens) / len(tokens)
    if avg_len < 4:
        return "beginner"
    if avg_len < 6:
        return "intermediate"
    return "advanced"


def _clean_sentence_for_example(sent: str) -> str:
    if not sent:
        return ""
    s = sent.strip()
    # Collapse internal whitespace
    s = re.sub(r"\s+", " ", s).strip()
    # Remove leading punctuation such as stray commas or quotes
    s = re.sub(r"^[,;:!?.\"\']+", "", s).strip()
    # Normalize trailing punctuation like ',.' or '.,' into a single mark
    s = re.sub(r"[ ,;:]+([.!?])$", r"\1", s)
    # Remove dangling comma/semicolon/colon if they are now terminal
    s = re.sub(r"[,;:]$", "", s)
    # Ensure sentence ends with a single terminator
    if not re.search(r"[.!?]$", s):
        s = s.rstrip(",;:") + "."
    return s


def _to_ing(word: str) -> str:
    w = word.lower()
    if w.endswith("e") and len(w) > 2:
        return w[:-1] + "ing"
    return w + "ing"


def _to_past(word: str) -> str:
    w = word.lower()
    if w.endswith("e"):
        return w + "d"
    if w.endswith("y") and len(w) > 1 and w[-2] not in "aeiou":
        return w[:-1] + "ied"
    return w + "ed"


def _pluralize(word: str) -> str:
    w = word.lower()
    if w.endswith("y") and w[-2] not in "aeiou":
        return w[:-1] + "ies"
    if w.endswith(("s", "ch", "sh", "x", "z")):
        return w + "es"
    return w + "s"


def _common_misspelling(word: str) -> str:
    w = word
    if len(w) > 3:
        i = 1
        swapped = w[:i] + w[i + 1 : i + 2] + w[i : i + 1] + w[i + 2 :]
        if swapped.lower() != w.lower():
            return swapped
    return w[:-1] if len(w) > 1 else w


def _unique_keep_first(items: List[str]) -> List[str]:
    out = []
    seen = set()
    for x in items:
        k = (x or "").strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


# Real English word lists for quality distractors (no synthetic nonsense)
COMMON_VERBS = [
    "go",
    "goes",
    "went",
    "come",
    "comes",
    "came",
    "take",
    "takes",
    "took",
    "make",
    "makes",
    "made",
    "get",
    "gets",
    "got",
    "give",
    "gives",
    "gave",
    "see",
    "sees",
    "saw",
    "know",
    "knows",
    "knew",
    "think",
    "thinks",
    "thought",
    "say",
    "says",
    "said",
    "tell",
    "tells",
    "told",
    "ask",
    "asks",
    "asked",
    "use",
    "uses",
    "used",
    "find",
    "finds",
    "found",
    "put",
    "puts",
    "try",
    "tries",
    "tried",
    "leave",
    "leaves",
    "left",
    "call",
    "calls",
    "called",
    "keep",
    "keeps",
    "kept",
    "let",
    "lets",
    "begin",
    "begins",
    "began",
    "seem",
    "seems",
    "seemed",
    "help",
    "helps",
    "helped",
    "show",
    "shows",
    "showed",
    "hear",
    "hears",
    "heard",
    "play",
    "plays",
    "played",
    "run",
    "runs",
    "ran",
    "move",
    "moves",
    "moved",
    "live",
    "lives",
    "lived",
    "believe",
    "believes",
    "hold",
    "holds",
    "held",
    "bring",
    "brings",
    "brought",
    "happen",
    "happens",
    "write",
    "writes",
    "wrote",
    "sit",
    "sits",
    "sat",
    "stand",
    "stands",
    "stood",
    "lose",
    "loses",
    "lost",
    "pay",
    "pays",
    "paid",
    "meet",
    "meets",
    "met",
    "walk",
    "walks",
    "walked",
    "eat",
    "eats",
    "ate",
    "drink",
    "drinks",
    "drank",
    "read",
    "reads",
    "sleep",
    "sleeps",
    "slept",
    "speak",
    "speaks",
    "spoke",
]

COMMON_NOUNS = [
    "time",
    "year",
    "people",
    "way",
    "day",
    "man",
    "woman",
    "child",
    "world",
    "life",
    "hand",
    "part",
    "place",
    "case",
    "week",
    "company",
    "system",
    "question",
    "work",
    "number",
    "night",
    "point",
    "home",
    "water",
    "room",
    "mother",
    "area",
    "money",
    "story",
    "fact",
    "month",
    "book",
    "eye",
    "job",
    "word",
    "business",
    "side",
    "kind",
    "head",
    "house",
    "friend",
    "father",
    "hour",
    "game",
    "line",
    "end",
    "member",
    "car",
    "city",
    "name",
    "team",
    "minute",
    "idea",
    "body",
    "back",
    "parent",
    "face",
    "door",
    "person",
    "teacher",
    "student",
    "school",
    "lesson",
    "class",
    "homework",
    "answer",
]

COMMON_ADJECTIVES = [
    "good",
    "new",
    "first",
    "last",
    "long",
    "great",
    "little",
    "own",
    "other",
    "old",
    "right",
    "big",
    "high",
    "different",
    "small",
    "large",
    "next",
    "early",
    "young",
    "important",
    "few",
    "bad",
    "same",
    "able",
    "free",
    "sure",
    "clear",
    "full",
    "special",
    "easy",
    "hard",
    "strong",
    "possible",
    "whole",
    "real",
    "best",
    "better",
    "true",
    "happy",
    "nice",
    "beautiful",
    "simple",
    "fast",
]


def _build_options_for_target(
    target: str, concept_hint: Optional[str] = None
) -> List[str]:
    """
    Create 4 plausible options including target using REAL English words only.
    Never generates nonsense like 'goesing', 'wordses', 'eated'.
    """
    t = target.strip()
    t_lower = t.lower()
    opts = [t]

    # Find semantically related real words based on concept
    if concept_hint == "third_person" or (
        t_lower.endswith("s") and not t_lower.endswith("ss")
    ):
        # For third person verbs, use real verb forms
        base = t_lower.rstrip("s")
        related = [
            v for v in COMMON_VERBS if v.startswith(base[:2]) and v.lower() != t_lower
        ]
        if len(related) < 3:
            related = [
                v
                for v in COMMON_VERBS
                if abs(len(v) - len(t)) <= 2 and v.lower() != t_lower
            ]
        opts.extend(related[:5])

    elif concept_hint == "verb_forms":
        # Use real verb variations
        related = [
            v
            for v in COMMON_VERBS
            if v.startswith(t_lower[:2]) and v.lower() != t_lower
        ]
        if len(related) < 3:
            related = random.sample(
                [v for v in COMMON_VERBS if v.lower() != t_lower],
                min(5, len(COMMON_VERBS) - 1),
            )
        opts.extend(related[:5])

    elif concept_hint == "article":
        # Article confusion options
        words = t.split()
        if words and words[0].lower() in ("a", "an", "the"):
            noun = " ".join(words[1:]) if len(words) > 1 else "item"
            opts = [t, f"the {noun}", f"a {noun}", f"an {noun}"]
        else:
            opts = [t, f"the {t}", f"a {t}", f"an {t}"]

    elif concept_hint == "preposition":
        # Preposition confusion with real prepositions
        preps = ["to", "at", "in", "on", "for", "with", "about", "from", "by"]
        opts = [t] + [p for p in preps if p.lower() != t_lower][:4]

    else:
        # General case: find similar real words
        all_words = COMMON_VERBS + COMMON_NOUNS + COMMON_ADJECTIVES
        if len(t) <= 5:
            similar = [
                w
                for w in all_words
                if abs(len(w) - len(t)) <= 1 and w.lower() != t_lower
            ]
        else:
            similar = [
                w
                for w in all_words
                if w.startswith(t_lower[0]) and w.lower() != t_lower
            ]
            if len(similar) < 3:
                similar = [
                    w
                    for w in all_words
                    if len(w) >= len(t) - 2 and w.lower() != t_lower
                ]
        if similar:
            opts.extend(random.sample(similar, min(5, len(similar))))

    # Deduplicate
    opts = _unique_keep_first(opts)

    # Ensure target is included
    if t not in opts:
        opts.insert(0, t)

    # Take first 4 unique options
    final = opts[:4]

    # If we still don't have 4, pad with common real words
    fallback_words = [
        "the",
        "and",
        "for",
        "are",
        "but",
        "not",
        "you",
        "all",
        "can",
        "her",
        "was",
        "one",
        "our",
    ]
    while len(final) < 4:
        for fw in fallback_words:
            if fw.lower() not in [f.lower() for f in final]:
                final.append(fw)
                break
        else:
            break
        if len(final) >= 4:
            break

    random.shuffle(final)

    # Ensure target is still present after shuffle
    if t not in final:
        final[0] = t

    return final[:4]
