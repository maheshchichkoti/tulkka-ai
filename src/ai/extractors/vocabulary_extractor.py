"""
High-quality, production-ready vocabulary extraction for Zoom transcripts.
- Captures real vocabulary students need
- Uses corrections, explicit teacher cues, and content-word heuristics
- Filters noise, names, fillers, and ultra-short words
- Designed to feed rule-based or LLM generators
"""

from typing import List, Dict
import re
import logging

logger = logging.getLogger(__name__)


class VocabularyExtractor:

    def __init__(self):
        # Words to always ignore (fillers, function words, ultra-basic words)
        self.skip_words = {
            # Function words
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "can",
            "could",
            "should",
            "may",
            "might",
            "must",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "this",
            "that",
            "these",
            "those",
            "okay",
            "ok",
            "hi",
            "hello",
            "bye",
            "yeah",
            "uh",
            "um",
            "hmm",
            "right",
            "and",
            "or",
            "but",
            "so",
            "if",
            "then",
            "when",
            "where",
            "what",
            "who",
            "how",
            "why",
            "which",
            "there",
            "here",
            "now",
            "just",
            "also",
            "very",
            "too",
            "more",
            "most",
            "some",
            "any",
            "all",
            "no",
            "not",
            "yes",
            "your",
            "my",
            "his",
            "her",
            "its",
            "our",
            "their",
            "me",
            "him",
            "us",
            "them",
            # Ultra-basic words (A1 level - too simple for exercises)
            "welcome",
            "today",
            "fine",
            "thank",
            "thanks",
            "nice",
            "meet",
            "good",
            "great",
            "well",
            "please",
            "sorry",
            "name",
            "like",
            "want",
            "need",
            "know",
            "think",
            "see",
            "look",
            "come",
            "go",
            "get",
            "make",
            "take",
            "give",
            "tell",
            "say",
            "ask",
            "use",
            "find",
            "put",
            "try",
            "let",
            "keep",
            "begin",
            "start",
            "stop",
            "open",
            "close",
            "read",
            "write",
            "learn",
            "teach",
            "work",
            "play",
            "help",
            "show",
            "call",
            "feel",
            "become",
            "leave",
            "bring",
            "happen",
            "turn",
            "move",
            "live",
            "believe",
            "hold",
            # Time/basic nouns
            "time",
            "day",
            "week",
            "month",
            "year",
            "morning",
            "evening",
            "night",
            "today",
            "tomorrow",
            "yesterday",
            "now",
            "then",
            # Classroom noise
            "okay",
            "alright",
            "right",
            "yes",
            "no",
            "maybe",
            "sure",
            # Known ASR artefact / noise in current transcripts
            "enforcement",
        }

        self.name_pattern = re.compile(r"^[A-Z][a-z]+$")
        self.word_pattern = re.compile(r"^[A-Za-z']+$")

    # ------------------------------------------------------------
    # PUBLIC EXTRACT FUNCTION
    # ------------------------------------------------------------
    def extract(self, transcript: str) -> List[Dict[str, str]]:
        if not transcript or not transcript.strip():
            return []

        vocab_items = []
        seen = set()

        cleaned = self._remove_speaker_labels(transcript)

        # 1) Highest-priority: extract from teacher corrections
        correction_vocab = self._extract_from_corrections(cleaned)
        for item in correction_vocab:
            w = item["word"].lower()
            if w not in seen:
                seen.add(w)
                vocab_items.append(item)
                if len(vocab_items) >= 15:
                    return vocab_items

        # 2) Extract explicit mentions like “new words: salad, camera, open”
        explicit = self._extract_explicit_vocab(cleaned)
        for item in explicit:
            w = item["word"].lower()
            if w not in seen:
                seen.add(w)
                vocab_items.append(item)
                if len(vocab_items) >= 15:
                    return vocab_items

        # 3) Extract content words from sentences
        content_words = self._extract_content_words(cleaned)
        for item in content_words:
            w = item["word"].lower()
            if w not in seen:
                seen.add(w)
                vocab_items.append(item)
                if len(vocab_items) >= 15:
                    break

        return vocab_items[:15]

    # ------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------
    def _remove_speaker_labels(self, text: str) -> str:
        return re.sub(r"[A-Za-z ]{1,40}:\s*", "", text)

    # ------------------------------------------------------------
    # 1) VOCAB FROM CORRECTIONS (highest value)
    # ------------------------------------------------------------
    def _extract_from_corrections(self, text: str) -> List[Dict[str, str]]:
        items = []

        # Match patterns like: not "speaking", say "speaking"
        patterns = [
            r"not\s+['\"]([^'\"]+)['\"]\s*,?\s*(?:say|use)\s+['\"]([^'\"]+)['\"]",
            r"don't say\s+['\"]([^'\"]+)['\"]\s*,?\s*say\s+['\"]([^'\"]+)['\"]",
            r"instead of\s+['\"]([^'\"]+)['\"]\s*,?\s*(?:use|say)\s+['\"]([^'\"]+)['\"]",
            r"['\"]([^'\"]+)['\"]\s+should\s+be\s+['\"]([^'\"]+)['\"]",
        ]

        for p in patterns:
            for m in re.finditer(p, text, re.IGNORECASE):
                incorrect = m.group(1).strip()
                correct = m.group(2).strip()

                if not correct or len(correct) < 3:
                    continue

                # keep correct word
                clean_word = re.sub(r"[^\w']+", "", correct)

                if len(clean_word) < 3:
                    continue

                items.append(
                    {
                        "word": clean_word.lower(),
                        "context": f"corrected: {incorrect} → {correct}",
                        "category": "corrected_usage",
                        "priority": "high",
                        "difficulty": self._difficulty(clean_word),
                    }
                )

        return items

    # ------------------------------------------------------------
    # 2) EXPLICIT VOCABULARY MENTION
    # e.g., "important words: salad, camera, open"
    # ------------------------------------------------------------
    def _extract_explicit_vocab(self, text: str) -> List[Dict[str, str]]:
        items = []
        pattern = r"(important|key|vocabulary|words?)\s*[:\-]\s*([^.]+)"

        for m in re.finditer(pattern, text, re.IGNORECASE):
            raw_list = m.group(2)
            tokens = re.split(r",|\band\b", raw_list)

            for t in tokens:
                w = t.strip().lower()
                if len(w) < 3:
                    continue
                if w in self.skip_words:
                    continue

                items.append(
                    {
                        "word": w,
                        "context": raw_list,
                        "category": "explicit_vocabulary",
                        "priority": "high",
                        "difficulty": self._difficulty(w),
                    }
                )

        return items

    # ------------------------------------------------------------
    # 3) CONTENT-WORD EXTRACTION
    # ------------------------------------------------------------
    def _extract_content_words(self, text: str) -> List[Dict[str, str]]:
        items = []
        tokens = re.findall(r"[A-Za-z']+", text)

        for token in tokens:
            w = token.lower()

            if w in self.skip_words:
                continue
            if len(w) < 4:
                continue
            if not self.word_pattern.match(token):
                continue
            if self.name_pattern.match(token):
                continue

            # Consider only nouns/verbs/adjectives-like patterns
            if not re.match(r"[A-Za-z]{3,20}", token):
                continue

            items.append(
                {
                    "word": w,
                    "context": "",
                    "category": "content_word",
                    "priority": "medium",
                    "difficulty": self._difficulty(w),
                }
            )

        return items

    # ------------------------------------------------------------
    def _difficulty(self, word: str) -> str:
        if not word:
            return "easy"
        if len(word) <= 4:
            return "easy"
        if len(word) <= 7:
            return "medium"
        return "hard"
