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

# Optional translator
try:
    from deep_translator import GoogleTranslator
    def _translator(target: str = "he"):
        lang = "iw" if target.lower() == "he" else target
        try:
            return GoogleTranslator(source="en", target=lang)
        except Exception:
            logger.warning("Translator init failed, falling back to None")
            return None
except Exception:
    GoogleTranslator = None
    def _translator(target: str = "he"):
        return None

def _tr(text: str, t) -> str:
    if not text or not t:
        return ""
    try:
        return t.translate(text)
    except Exception:
        return ""

COMMON_WORDS = {
    "open", "close", "name", "please", "camera", "hello",
    "thank", "fine", "great", "eat", "go", "have", "is", "are"
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
    s = re.sub(r'^[,;:!?.\"\']+', "", s).strip()
    # Normalize trailing punctuation like ',.' or '.,' into a single mark
    s = re.sub(r"[ ,;:]+([.!?])$", r"\1", s)
    # Remove dangling comma/semicolon/colon if they are now terminal
    s = re.sub(r"[,;:]$", "", s)
    # Ensure sentence ends with a single terminator
    if not re.search(r"[.!?]$", s):
        s = s.rstrip(',;:') + "."
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
        swapped = w[:i] + w[i+1:i+2] + w[i:i+1] + w[i+2:]
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

def _build_options_for_target(target: str, concept_hint: Optional[str] = None) -> List[str]:
    t = target.strip()
    opts = [t]
    if re.match(r"^[A-Za-z']+$", t) and " " not in t:
        candidates = [
            _to_ing(t),
            _to_past(t),
            _pluralize(t),
            _common_misspelling(t),
            t.capitalize(),
        ]
        opts.extend(c for c in candidates if c and c.lower() != t.lower())
    else:
        base = re.sub(r"[^\w\s]", "", t)
        words = base.split()
        content = next((w for w in words if len(w) > 3), words[0])
        opts.extend([
            base.replace(content, _pluralize(content)),
            base.replace(content, _to_ing(content)),
            base.replace(content, _common_misspelling(content)),
            base.replace(content, content.capitalize()),
        ])
    if concept_hint == "third_person":
        opts = [
            t,
            (t.rstrip("s")),
            (t + "s"),
            _to_ing(t),
            _common_misspelling(t),
        ]
    elif concept_hint == "article":
        words = t.split()
        noun = " ".join(words[1:]) if words and words[0] in ("a", "an", "the") else t
        opts = [t, f"the {noun}", f"a {noun}", f"an {noun}", noun]
    elif concept_hint == "preposition":
        swaps = ["to", "at", "in", "on", "for", "with", "about"]
        parts = t.split()
        if len(parts) >= 3:
            mid = min(2, len(parts) - 2)
            noun = parts[mid + 1]
            candidates = [f"{' '.join(parts[:mid])} {p} {noun}" for p in swaps]
            opts = [t] + candidates
    opts = _unique_keep_first(opts)
    if t not in opts:
        opts.insert(0, t)
    final = opts[:4]
    while len(final) < 4:
        final.append(t + str(random.randint(1, 99)))
    random.shuffle(final)
    if t not in final:
        final[0] = t
    return final
