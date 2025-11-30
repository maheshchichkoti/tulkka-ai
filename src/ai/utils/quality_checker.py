"""
Quality assurance for generated exercises
Fully compatible with NEW rule-based generators (2025)
"""

from typing import List, Dict
import logging
import re

logger = logging.getLogger(__name__)

class QualityChecker:
    """Validates exercise quality before output (production-ready)"""

    def __init__(self):
        self.errors = []
        self.warnings = []

    # -------------------------------------------------
    # MAIN ENTRY
    # -------------------------------------------------
    def validate_exercises(self, fill_blank, flashcards, spelling) -> bool:
        self.errors = []
        self.warnings = []

        self._check_fill_blank(fill_blank)
        self._check_flashcards(flashcards)
        self._check_spelling(spelling)

        total = len(fill_blank) + len(flashcards) + len(spelling)

        if total < 8:
            self.warnings.append(f"Total exercises = {total}, below minimum (8)")
        elif total > 40:
            self.warnings.append(f"Total exercises = {total}, unusually high")

        # Logging
        if self.errors:
            logger.warning(f"Quality check: {len(self.errors)} errors found")
            for e in self.errors[:5]:
                logger.warning("  - " + e)

        if self.warnings:
            logger.info(f"Quality check: {len(self.warnings)} warnings")
            for w in self.warnings[:5]:
                logger.info("  - " + w)

        return len(self.errors) == 0

    # -------------------------------------------------
    # FILL-IN-THE-BLANK CHECKER
    # -------------------------------------------------
    def _check_fill_blank(self, items: List[Dict]):
        for i, ex in enumerate(items):
            ix = i + 1

            # Sentence must contain a blank
            sentence = ex.get("sentence", "")
            if "_____" not in sentence:
                self.errors.append(f"Fill-blank {ix}: Missing blank marker")

            # Options must be a list of 4 strings
            options = ex.get("options")
            if not isinstance(options, list) or len(options) != 4:
                self.errors.append(f"Fill-blank {ix}: Options must be a list of 4")
                continue

            # No empty options
            empty = [opt for opt in options if not opt or not str(opt).strip()]
            if empty:
                self.errors.append(f"Fill-blank {ix}: Contains empty options")

            # Duplicate options
            if len(set(options)) < 4:
                self.warnings.append(f"Fill-blank {ix}: Duplicate options")

            # Correct answer must exist and be in options
            answer = ex.get("correct_answer", "")
            if not answer:
                self.errors.append(f"Fill-blank {ix}: Missing correct_answer")
            elif answer not in options:
                self.errors.append(f"Fill-blank {ix}: correct_answer not in options")

            # Sentence length warning
            if len(sentence.split()) < 5:
                self.warnings.append(f"Fill-blank {ix}: Sentence too short")

    # -------------------------------------------------
    # FLASHCARD CHECKER
    # -------------------------------------------------
    def _check_flashcards(self, cards: List[Dict]):
        seen = set()
        for i, card in enumerate(cards):
            ix = i + 1
            word = card.get("word", "")

            if not word:
                self.errors.append(f"Flashcard {ix}: Missing word")
                continue

            # Duplicate detection
            lw = word.lower()
            if lw in seen:
                self.warnings.append(f"Flashcard {ix}: duplicate word '{word}'")
            seen.add(lw)

            # Must have translation
            if not card.get("translation"):
                self.errors.append(f"Flashcard {ix}: Missing translation")

            # Example sentence check
            example = card.get("example_sentence", "")
            if not example:
                self.warnings.append(f"Flashcard {ix}: Missing example_sentence")
            else:
                # Should contain word or a related form
                if word.lower() not in example.lower():
                    self.warnings.append(
                        f"Flashcard {ix}: Example sentence does not contain word"
                    )

            # Difficulty field is required
            if "difficulty" not in card:
                self.warnings.append(f"Flashcard {ix}: Missing difficulty metadata")

    # -------------------------------------------------
    # SPELLING CHECKER
    # -------------------------------------------------
    def _check_spelling(self, items: List[Dict]):
        seen = set()
        for i, ex in enumerate(items):
            ix = i + 1
            word = ex.get("word", "")

            if not word:
                self.errors.append(f"Spelling {ix}: Missing word")
                continue

            # Duplicate detection
            lw = word.lower()
            if lw in seen:
                self.errors.append(f"Spelling {ix}: Duplicate word '{word}'")
            seen.add(lw)

            # Must have translation
            if not ex.get("translation"):
                self.errors.append(f"Spelling {ix}: Missing translation")

            # Must have hint field
            if not ex.get("hint"):
                self.warnings.append(f"Spelling {ix}: Missing hint field")

            # Difficulty field required
            if "difficulty" not in ex:
                self.warnings.append(f"Spelling {ix}: Missing difficulty metadata")

            # Too-short word (spelling should be challenge)
            if len(word) < 3:
                self.warnings.append(f"Spelling {ix}: Word too short to be meaningful")
