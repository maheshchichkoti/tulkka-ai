# src/ai/generators/sentence_builder_generator.py
"""
Sentence builder exercise generator.

Generates exercises where students arrange words to form correct sentences.
Uses clean, pedagogically sound sentences - never transcript noise.
"""

from __future__ import annotations
import uuid
import re
from typing import List, Dict, Any, Set
from .shared_utils import _translator, _tr, _clean_sentence_for_example, _assess_difficulty

# Noise patterns to filter out
NOISE_WORDS: Set[str] = {"okay", "ok", "um", "uh", "hmm", "yeah", "right", "so", "well"}
NOISE_NAMES: Set[str] = {"khadija", "basmala", "emam", "mahaba", "philip", "pass"}

# Clean fallback sentences for sentence builder
FALLBACK_SENTENCES = [
    "Can you open the window, please?",
    "I think you already know the answer.",
    "What did you do in the morning?",
    "She goes to school every day.",
    "We had a great time at the party.",
    "Please write your name on the paper.",
    "I want to learn a new language.",
    "The weather is very nice today.",
    "Can I ask you a question?",
    "I wake up early in the morning.",
]


def _is_clean_for_builder(sentence: str) -> bool:
    """Check if a sentence is suitable for sentence builder exercises."""
    if not sentence:
        return False
    
    words = sentence.split()
    
    # Must have 4-10 words (not too short, not too long)
    if len(words) < 4 or len(words) > 12:
        return False
    
    lower = sentence.lower()
    
    # Skip sentences with names
    if any(name in lower for name in NOISE_NAMES):
        return False
    
    # Skip sentences starting with filler words
    first_word = words[0].lower().rstrip(".,!?")
    if first_word in NOISE_WORDS:
        return False
    
    # Skip sentences with ellipsis
    if "..." in sentence or "…" in sentence:
        return False
    
    # Must end with proper punctuation
    if sentence.rstrip()[-1] not in ".!?":
        return False
    
    # Skip malformed sentences
    if re.search(r"[,;:]\s*[.!?]$", sentence):
        return False
    
    return True


def generate_sentence_builder(sentences: List[Dict[str, Any]], *, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Generate sentence builder exercises from extracted sentences.
    
    Args:
        sentences: List of sentence dictionaries
        limit: Maximum number of exercises to generate
    
    Returns:
        List of sentence builder exercise dictionaries.
    """
    t = _translator("he")
    out: List[Dict[str, Any]] = []
    cnt = 0
    used_sentences: Set[str] = set()
    
    # First pass: try to use provided sentences that are clean
    for s in (sentences or []):
        if cnt >= limit:
            break
        if isinstance(s, dict):
            sent = s.get("sentence") or s.get("text") or s.get("english_sentence") or ""
        else:
            sent = str(s)
        sent = sent.strip()
        if not sent:
            continue
        
        clean = _clean_sentence_for_example(sent)
        
        # Capitalise first letter if not already
        if clean and clean[0].islower():
            clean = clean[0].upper() + clean[1:]
        
        # Convert to question if needed
        if clean.endswith(".") and re.match(r"^(can|could|what|why|how|where|when|do|does|did|is|are|am|will|would|shall|should|have|has|had)\b", clean, re.I):
            clean = clean[:-1] + "?"
        
        # Check if sentence is clean enough
        if not _is_clean_for_builder(clean):
            continue
        
        # Skip duplicates
        if clean.lower() in used_sentences:
            continue
        
        words_only = re.findall(r"[A-Za-z']+", clean)
        
        # Skip sentences with mid-sentence capitalized words (likely names)
        if any(w[0].isupper() and i != 0 for i, w in enumerate(words_only)):
            continue
        
        used_sentences.add(clean.lower())
        tokens = re.findall(r"[A-Za-z']+|[,\.\.!?;:]", clean)
        accepted = [tokens]
        translation = _tr(clean, t) if t else ""
        hint = "Rebuild the sentence in the correct order."
        difficulty = _assess_difficulty(clean)
        
        out.append({
            "id": str(uuid.uuid4()),
            "english": clean,
            "tokens": tokens,
            "accepted": accepted,
            "translation": translation,
            "hint": hint,
            "difficulty": difficulty,
        })
        cnt += 1
    
    # Second pass: fill with fallback sentences if needed
    for fallback in FALLBACK_SENTENCES:
        if cnt >= limit:
            break
        if fallback.lower() in used_sentences:
            continue
        
        used_sentences.add(fallback.lower())
        tokens = re.findall(r"[A-Za-z']+|[,\.\.!?;:]", fallback)
        accepted = [tokens]
        translation = _tr(fallback, t) if t else ""
        
        out.append({
            "id": str(uuid.uuid4()),
            "english": fallback,
            "tokens": tokens,
            "accepted": accepted,
            "translation": translation,
            "hint": "Rebuild the sentence in the correct order.",
            "difficulty": _assess_difficulty(fallback),
        })
        cnt += 1
    
    return out[:limit]
