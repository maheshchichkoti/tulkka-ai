"""
Production-ready MistakeExtractor
- High accuracy
- Noise resistant
- Includes metadata: difficulty, confidence, source, role, rule
- Fully compatible with new rule-based generators
"""

from typing import List, Dict, Optional
import re
import uuid
import logging

logger = logging.getLogger(__name__)

_MAX_RETURNS = 15
_MAX_STR_LEN = 180


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def _clean_text(s: str) -> str:
    if not s:
        return ""
    s = s.strip()
    s = re.sub(r'[\u2018\u2019\u201c\u201d]', '', s)  # smart quotes
    s = re.sub(r'\s+', ' ', s)
    return s.strip(" .,:;!?()[]\"'")

def _difficulty(text: str) -> str:
    if not text:
        return "beginner"
    words = text.split()
    if len(words) <= 2:
        return "beginner"
    if len(words) <= 5:
        return "intermediate"
    return "advanced"

def _confidence(incorrect: str, correct: str) -> float:
    """Very simple heuristic: similarity score"""
    if not incorrect or not correct:
        return 0.3
    inc = incorrect.lower().split()
    cor = correct.lower().split()
    shared = len(set(inc) & set(cor))
    total = max(len(set(inc)), len(set(cor)), 1)
    return max(0.3, min(1.0, shared / total + 0.2))


# ---------------------------------------------------------
# MistakeExtractor
# ---------------------------------------------------------
class MistakeExtractor:

    def __init__(self):
        # Core patterns
        self.patterns = [
            # “Don’t say X, say Y”
            (re.compile(r"(?:don't say|not)\s+['\"](.+?)['\"]\s*,?\s*(?:say|use)\s+['\"](.+?)['\"]", re.I), "pair"),

            # “Instead of X, say Y”
            (re.compile(r"instead of ['\"](.+?)['\"]\s*,?\s*(?:use|say)\s+['\"](.+?)['\"]", re.I), "pair"),

            # “‘X’ should be ‘Y’”
            (re.compile(r"['\"](.+?)['\"]\s+should be\s+['\"](.+?)['\"]", re.I), "pair"),

            # “It should be Y”
            (re.compile(r"(?:it )?should be\s+['\"](.+?)['\"]", re.I), "correction"),

            # “Correct sentence is …”
            (re.compile(r"(?:correct|correction)[: ]+(.+?)(?:[\.!\?]|$)", re.I), "correction"),
        ]

    # -----------------------------------------------------
    def extract(self, transcript: str) -> List[Dict]:
        if not transcript:
            return []

        # Normalize speakers
        text = re.sub(r"\s*([A-Za-z][A-Za-z ]{0,40}:)", r"\n\1", transcript)

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        utterances = []
        speaker_re = re.compile(r"^([^:]+):\s*(.*)$")

        roles = {}             # raw speaker -> Teacher/Student
        teacher_seen = False
        student_seen = False
        last_role = None

        # ----------------------------------------
        # Parse speakers
        # ----------------------------------------
        for ln in lines:
            m = speaker_re.match(ln)
            if m:
                raw_label, content = m.group(1), m.group(2)
                key = raw_label.lower()
                role = roles.get(key)

                if not role:
                    if not teacher_seen:
                        role = "Teacher"
                        teacher_seen = True
                    elif not student_seen:
                        role = "Student"
                        student_seen = True
                    else:
                        role = last_role or "Teacher"
                    roles[key] = role

                utterances.append((role, _clean_text(content)))
                last_role = role
            else:
                # no speaker: merge with last
                if utterances:
                    r, c = utterances[-1]
                    utterances[-1] = (r, c + " " + _clean_text(ln))
                else:
                    utterances.append(("Unknown", _clean_text(ln)))

        # ----------------------------------------
        # Extract mistakes
        # ----------------------------------------
        mistakes = []
        seen = set()
        last_student = ""

        for role, content in utterances:
            if role == "Student":
                last_student = content
                continue

            if role != "Teacher":
                continue

            # Ignore noise
            if content.lower() in ("okay", "yes", "good", "right"):
                continue

            for pat, mode in self.patterns:
                for m in pat.finditer(content):
                    if mode == "pair":
                        incorrect = _clean_text(m.group(1))
                        correct = _clean_text(m.group(2))
                    else:
                        correct = _clean_text(m.group(1))
                        incorrect = last_student or ""

                    if not incorrect or not correct:
                        continue
                    if incorrect.lower() == correct.lower():
                        continue

                    key = (incorrect.lower(), correct.lower())
                    if key in seen:
                        continue
                    seen.add(key)

                    mistakes.append(self._build_mistake(
                        incorrect=incorrect,
                        correct=correct,
                        context=content
                    ))

                    if len(mistakes) >= _MAX_RETURNS:
                        return mistakes

        return mistakes

    # -----------------------------------------------------
    # Build enriched mistake object
    # -----------------------------------------------------
    def _build_mistake(self, incorrect: str, correct: str, context: str):
        mistake_type = self._categorize_mistake(incorrect, correct)

        return {
            "id": str(uuid.uuid4()),
            "incorrect": incorrect[:_MAX_STR_LEN],
            "correct": correct[:_MAX_STR_LEN],
            "type": mistake_type,
            "rule": self._rule_for(mistake_type),
            "context": context[:120],
            "difficulty": _difficulty(correct),
            "confidence": round(_confidence(incorrect, correct), 2),
            "source": "mistake_extractor"
        }

    # -----------------------------------------------------
    # Categorization
    # -----------------------------------------------------
    def _categorize_mistake(self, incorrect: str, correct: str) -> str:
        inc = incorrect.lower()
        cor = correct.lower()

        # Very small handcrafted rules
        if re.search(r"\bgo|goes|went|eat|ate|eats|playing|played\b", inc + " " + cor):
            return "verb_tense"

        if re.search(r"\b(a|an|the)\b", inc) != re.search(r"\b(a|an|the)\b", cor):
            return "article"

        if inc.endswith("s") != cor.endswith("s"):
            return "plural"

        if "to " in cor and "to " not in inc:
            return "preposition"

        return "general"

    # -----------------------------------------------------
    def _rule_for(self, t: str) -> str:
        rules = {
            "verb_tense": "Use the correct verb tense (present/past).",
            "article": "Use articles (a/an/the) correctly.",
            "plural": "Use plural form when needed.",
            "preposition": "Use correct prepositions.",
            "general": "Follow standard grammar rules."
        }
        return rules.get(t, "Check grammar and structure.")
