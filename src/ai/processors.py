# src/ai/processors.py
"""
Transcript processing helpers:
- clean_transcript_text: normalize whitespace, remove speaker headers, remove repeated noise tokens
- split_into_paragraphs: chunking to smaller units suitable for generators
- extract_keywords: lightweight frequency-based keywords excluding stopwords
"""

from __future__ import annotations
import re
import logging
from typing import List, Tuple, Dict
from collections import Counter

logger = logging.getLogger(__name__)

# minimal stopword list; add languages as needed or load from file
STOPWORDS = {
    "the","is","a","an","and","or","but","if","then","so","we","you","they","i","he","she","it",
    "to","of","in","on","for","with","that","this","are","was","were","be","been","have","has","had",
}

SPEAKER_PREFIX_RE = re.compile(r"^(?:[A-Za-z0-9_ ]{1,50}:)\s*", flags=re.M)

def clean_transcript_text(text: str) -> str:
    """
    Clean raw transcript text (VTT-derived or ASR output).
    - strip WEBVTT artifacts
    - remove speaker labels like "John: "
    - remove URLs
    - collapse whitespace
    """
    if not text:
        return ""
    # Remove common VTT timestamps and cues (defensive)
    text = re.sub(r"WEBVTT.*", "", text, flags=re.I)
    text = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}", " ", text)
    text = re.sub(r"\[.*?\]", " ", text)  # remove bracketed notes
    text = re.sub(r"https?://\S+", " ", text)
    # Remove speaker prefixes (e.g. "John Doe: Hello")
    text = SPEAKER_PREFIX_RE.sub("", text)
    # Remove repeated non-speech tokens (e.g., "um", "uh" repeated)
    text = re.sub(r"\b(um|uh|erm|ah|mm)\b(?:\s+\1\b){1,}", r"\1", text, flags=re.I)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

def split_into_paragraphs(text: str, max_chars: int = 1500) -> List[str]:
    """
    Split text into paragraphs/chunks under max_chars, prefer splitting at sentence boundaries.
    Returns list of cleaned paragraph strings.
    """
    if not text:
        return []
    # sentence-like split
    candidates = re.split(r'(?<=[\.\?\!])\s+', text)
    chunks = []
    current = []
    current_len = 0
    for s in candidates:
        if not s:
            continue
        s = s.strip()
        if current_len + len(s) + 1 > max_chars and current:
            chunks.append(" ".join(current).strip())
            current = [s]
            current_len = len(s)
        else:
            current.append(s)
            current_len += len(s) + 1
    if current:
        chunks.append(" ".join(current).strip())
    # final pass: ensure no chunk is empty
    return [c for c in chunks if c]

def extract_keywords(text: str, top_n: int = 12) -> List[Tuple[str, int]]:
    """
    Very small keyword extractor: token frequency excluding stopwords and short tokens.
    Returns list of (token, count) sorted by frequency.
    """
    if not text:
        return []
    words = re.findall(r"[A-Za-z']{2,}", text.lower())
    filtered = [w for w in words if w not in STOPWORDS]
    ctr = Counter(filtered)
    common = ctr.most_common(top_n)
    return common
