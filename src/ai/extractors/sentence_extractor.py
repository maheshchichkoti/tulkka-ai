"""
Production-ready SentenceExtractor
- Robust sentence extraction from noisy Zoom transcripts
- Returns high-quality practice-worthy sentences
- Includes metadata: difficulty, confidence, length, source, tokens
"""

from typing import List, Dict
import re
import logging

logger = logging.getLogger(__name__)


class SentenceExtractor:

    def __init__(self):
        # Controlled window for “practice-worthy” sentences
        self.min_words = 5
        self.max_words = 20

    # ----------------------------------------------------
    def extract(self, transcript: str) -> List[Dict[str, str]]:
        if not transcript or not transcript.strip():
            return []

        sentences = []
        seen = set()

        text = self._normalize(transcript)
        raw_chunks = self._split_into_sentences(text)

        for chunk in raw_chunks:
            clean = chunk.strip()
            if not clean:
                continue

            # Word count filtering
            words = clean.split()
            wc = len(words)
            if wc < self.min_words or wc > self.max_words:
                continue

            # Ignore commands (e.g., "open camera please")
            if self._looks_like_command(clean):
                continue

            # Must contain real English content
            if not re.search(r"[A-Za-z]", clean):
                continue

            # Remove duplicates
            key = clean.lower()
            if key in seen:
                continue
            seen.add(key)

            metadata = self._build_metadata(clean)

            sentences.append(metadata)

            if len(sentences) >= 15:
                break

        return sentences

    # ----------------------------------------------------
    # Cleaning / Splitting Logic
    # ----------------------------------------------------
    def _normalize(self, text: str) -> str:
        """Remove speaker names, artifacts, repeated fillers."""
        # Remove "Teacher:", "Student:", or any speaker-like prefix
        text = re.sub(r"\b[A-Za-z][A-Za-z ]{0,25}:\s*", "", text)

        # Remove common Zoom filler junk
        # Also strip any immediate following comma/space so we don't leave leading ', '
        text = re.sub(r"\b(okay|yeah|uh|um|hmm|right|you know)\b[, ]*", "", text, flags=re.I)

        # Normalize spacing
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split on punctuation or long pauses."""
        # Ensure punctuation exists before splitting
        text = re.sub(r"([.!?])", r"\1 ", text)
        text = re.sub(r"\s+", " ", text)

        parts = re.split(r"[.!?]+", text)
        return [p.strip() for p in parts if p.strip()]

    def _looks_like_command(self, s: str) -> bool:
        """Detect teacher commands such as: 'open the camera please'."""
        cmd_keywords = ["open", "close", "repeat", "listen", "say", "answer", "look", "start", "begin"]
        w = s.lower().split()
        if len(w) <= 6:
            if any(w[0].startswith(k) for k in cmd_keywords):
                return True
        return False

    # ----------------------------------------------------
    # Metadata
    # ----------------------------------------------------
    def _build_metadata(self, sentence: str) -> Dict[str, str]:
        tokens = re.findall(r"[A-Za-z']+", sentence)
        difficulty = self._difficulty(sentence)
        conf = self._confidence(tokens)

        return {
            "sentence": sentence,
            "english_sentence": sentence,
            "difficulty": difficulty,
            "confidence": conf,
            "length": len(tokens),
            "tokens": tokens,
            "source": "sentence_extractor"
        }

    def _difficulty(self, s: str) -> str:
        tokens = s.split()
        avg = sum(len(t) for t in tokens) / max(1, len(tokens))
        if avg < 4:
            return "easy"
        if avg < 6:
            return "medium"
        return "hard"

    def _confidence(self, tokens: List[str]) -> float:
        """
        Simple heuristic:
        - more tokens = more reliable
        - content words boost confidence
        """
        if not tokens:
            return 0.3

        content = [t for t in tokens if len(t) > 4]
        score = 0.3 + (len(content) / max(3, len(tokens)))  # 0.3 → 1.0
        return round(min(score, 1.0), 2)
