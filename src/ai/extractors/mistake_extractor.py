# src/ai/extractors/mistake_extractor.py
"""Robust mistake extraction from lesson transcripts (production-ready)."""
from typing import List, Dict, Tuple, Optional
import re
import logging

logger = logging.getLogger(__name__)

_MAX_RETURNS = 15
_MAX_STR_LEN = 200

def _clean_phrase(s: str) -> str:
    # remove surrounding quotes, trim, collapse whitespace, strip trailing punctuation
    if not s:
        return ""
    s = s.strip()
    s = re.sub(r'^[\"\']+|[\"\']+$', '', s)
    s = re.sub(r'[\u2018\u2019\u201c\u201d]', '', s)  # smart quotes
    s = re.sub(r'\s+', ' ', s)
    s = s.strip(' .,:;!?')
    return s.strip()

class MistakeExtractor:
    """Extract student mistakes and corrections from lesson transcripts."""

    def __init__(self):
        # Patterns: (regex, mode)
        # mode: "pair" => captures (incorrect, correct)
        #       "reverse_pair" => captures (correct, incorrect) (rare)
        #       "correction" => captures only correct (use last_student_text as incorrect)
        self.correction_patterns = [
            # "not 'X', say 'Y'" or "don't say 'X', say 'Y'"
            (re.compile(r"(?:not|don't\s+say)\s+['\"]([^'\"]+)['\"]\s*,?\s*(?:say|use|it's)\s+['\"]([^'\"]+)['\"]", re.I), "pair"),
            # "instead of 'X', use 'Y'"
            (re.compile(r"instead\s+of\s+['\"]([^'\"]+)['\"]\s*,?\s*(?:use|say)\s+['\"]([^'\"]+)['\"]", re.I), "pair"),
            # "'X' should be 'Y'"
            (re.compile(r"['\"]([^'\"]+)['\"]\s+should\s+be\s+['\"]([^'\"]+)['\"]", re.I), "pair"),
            # "should be 'Y' (not 'X')" -> reverse order
            (re.compile(r"should\s+be\s+['\"]([^'\"]+)['\"]\s*(?:not|instead\s+of)\s+['\"]([^'\"]+)['\"]", re.I), "reverse_pair"),
            # "Correction: X" / "Correct: X" / "The correct sentence is X"
            (re.compile(r"(?:correction|correct(?:ion)?|the correct (?:sentence|form|way) is)[:\s]+(.+?)(?:[\.!\?]|$)", re.I), "correction"),
            # "It should be X"
            (re.compile(r"(?:it )?should be[:\s]+(.+?)(?:[\.!\?]|$)", re.I), "correction"),
            # "Better: X" / "Better to say X"
            (re.compile(r"better(?:\s+to\s+say)?[:\s]+(.+?)(?:[\.!\?]|$)", re.I), "correction"),
            # "Careful: X"
            (re.compile(r"careful!?[:\s]+(.+?)(?:[\.!\?]|$)", re.I), "correction"),
        ]

    def extract(self, transcript: str) -> List[Dict[str, str]]:
        if not transcript:
            return []

        # Normalize transcript text
        text = re.sub(r'\r\n?', '\n', transcript)
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)

        # Split into utterances while retaining speaker labels
        # This yields items like "Teacher: ...", "Student: ..."
        utterances = []
        # split on lines, but keep lines that have "Teacher:" or "Student:" or raw text
        lines = [ln.strip() for ln in re.split(r'\n+', text) if ln.strip()]
        speaker_re = re.compile(r'^(Teacher|Student)\b[:\-]?\s*(.*)$', re.I)
        for ln in lines:
            m = speaker_re.match(ln)
            if m:
                speaker = m.group(1).capitalize()
                content = m.group(2).strip()
                utterances.append((speaker, content))
            else:
                # if no explicit speaker, treat as free text; attach to last speaker if exists
                if utterances:
                    last_speaker, last_content = utterances[-1]
                    utterances[-1] = (last_speaker, f"{last_content} {ln}".strip())
                else:
                    utterances.append(("Unknown", ln))

        mistakes: List[Dict[str, str]] = []
        seen: set = set()
        last_student_text = ""

        # Primary pass: teacher utterances parsed by patterns
        for idx, (speaker, content) in enumerate(utterances):
            if speaker.lower().startswith("student"):
                if content:
                    last_student_text = _clean_phrase(content)[:_MAX_STR_LEN]
                continue
            if not speaker.lower().startswith("teacher"):
                # skip unknown speakers for corrections
                continue

            teacher_text = content or ""
            teacher_text_clean = teacher_text.strip()

            # Apply patterns
            for pattern, mode in self.correction_patterns:
                for match in pattern.finditer(teacher_text_clean):
                    if mode == "pair":
                        inc_raw, cor_raw = match.group(1), match.group(2)
                        incorrect = _clean_phrase(inc_raw)
                        correct = _clean_phrase(cor_raw)
                    elif mode == "reverse_pair":
                        cor_raw, inc_raw = match.group(1), match.group(2)
                        incorrect = _clean_phrase(inc_raw)
                        correct = _clean_phrase(cor_raw)
                    else:  # "correction" single capture
                        correct = _clean_phrase(match.group(1))
                        incorrect = last_student_text

                    # Basic validation
                    if not correct:
                        continue
                    if not incorrect:
                        # if we don't have student context, skip single-capture corrections
                        if mode == "correction":
                            continue
                        # otherwise try to infer incorrect from surrounding teacher text (very small heuristic)
                        # attempt to find a parenthetical "(not X)" inside teacher_text
                        paren = re.search(r'\(not\s+([^\)]+)\)', teacher_text_clean, re.I)
                        if paren:
                            incorrect = _clean_phrase(paren.group(1))
                    if not incorrect:
                        continue

                    # Prevent trivial or identical pairs
                    if incorrect.lower() == correct.lower():
                        continue
                    if len(correct.split()) < 1 or len(incorrect.split()) < 1:
                        continue

                    key = (incorrect.lower()[:60], correct.lower()[:60])
                    if key in seen:
                        continue

                    mistake_type = self._categorize_mistake(incorrect, correct)
                    mistakes.append({
                        "incorrect": incorrect[:_MAX_STR_LEN],
                        "correct": correct[:_MAX_STR_LEN],
                        "type": mistake_type,
                        "context": (_clean_phrase(match.group(0))[:120] if match else teacher_text_clean[:120]),
                        "rule": self._get_grammar_rule(mistake_type)
                    })
                    seen.add(key)
                    if len(mistakes) >= _MAX_RETURNS:
                        return mistakes[:_MAX_RETURNS]

        # Fallback pass: adjacent Student -> Teacher that looks like correction
        for i in range(len(utterances) - 1):
            spk, scont = utterances[i]
            nspk, ncont = utterances[i + 1]
            if not spk.lower().startswith("student") or not nspk.lower().startswith("teacher"):
                continue
            student_text = _clean_phrase(scont)
            teacher_text = _clean_phrase(ncont)
            if not student_text or not teacher_text:
                continue
            # skip praise/questions
            if teacher_text.endswith('?') or re.match(r'^(good|nice|great|excellent|perfect)\b', teacher_text, re.I):
                continue
            # length heuristics
            if len(teacher_text) < 6 or len(teacher_text) > 150:
                continue
            # overlap heuristic: partial overlap but not identical
            s_words = set(student_text.lower().split())
            t_words = set(teacher_text.lower().split())
            overlap = len(s_words & t_words) / max(1, len(s_words))
            if 0.15 < overlap < 0.95:
                key = (student_text[:60].lower(), teacher_text[:60].lower())
                if key in seen:
                    continue
                mistake_type = self._categorize_mistake(student_text, teacher_text)
                mistakes.append({
                    "incorrect": student_text[:_MAX_STR_LEN],
                    "correct": teacher_text[:_MAX_STR_LEN],
                    "type": mistake_type,
                    "context": f"{student_text[:80]} → {teacher_text[:80]}",
                    "rule": self._get_grammar_rule(mistake_type)
                })
                seen.add(key)
                if len(mistakes) >= _MAX_RETURNS:
                    break

        return mistakes[:_MAX_RETURNS]

    def _categorize_mistake(self, incorrect: str, correct: str) -> str:
        # lightweight heuristics for common error types
        inc = incorrect.lower()
        cor = correct.lower()

        # verb tense / verb form
        if re.search(r'\b(am|is|are|was|were|eat|eats|went|go|going|gone|bought|buy|buying|ate)\b', inc) and \
           re.search(r'\b(went|ate|bought|gone|eaten|played|played|cooked)\b', cor):
            return 'grammar_verb_tense'

        # subject-verb agreement (simple)
        if re.search(r'\b(i|we|you|they)\b', inc) and re.search(r'\b(s)\b', cor):
            # weak heuristic; exact patterns checked below
            pass
        if 'eats' in inc and 'eat' in cor:
            return 'grammar_subject_verb_agreement'

        # article errors
        if re.search(r'\b(is|was|be)\b.*\b(engineer|teacher|doctor|student)\b', inc) and \
           re.search(r'\b(is|was|be)\b.*\b(an |a )', cor):
            return 'grammar_article'

        # plural errors
        if (re.search(r'\b\w+s?\b', inc) and re.search(r'\b\w+s\b', cor)) or \
           (re.search(r'\begg\b', inc) and 'eggs' in cor):
            return 'grammar_plural'

        # preposition
        if 'listening music' in inc and 'listening to music' in cor:
            return 'grammar_preposition'

        # gerund/infinitive
        if re.search(r'\blike\b\s+\w+\b', inc) and re.search(r'\blike\b\s+\w+ing\b', cor):
            return 'grammar_gerund_infinitive'

        # word form
        if 'comfort' in inc and 'comfortable' in cor:
            return 'vocabulary_word_form'

        # sentence structure fallback
        if len(inc.split()) >= 3 and len(cor.split()) >= 3:
            # heuristic: if many tokens differ, likely structure
            inc_set = set(inc.split())
            cor_set = set(cor.split())
            diff = len(cor_set - inc_set)
            if diff > 1:
                return 'grammar_sentence_structure'

        return 'grammar_general'

    def _get_grammar_rule(self, mistake_type: str) -> str:
        rules = {
            'grammar_verb_tense': 'Use correct verb tense (present simple, past simple, etc.)',
            'grammar_subject_verb_agreement': 'Verb must agree with subject (I eat, he eats)',
            'grammar_article': 'Use articles (a/an) before singular countable nouns',
            'grammar_plural': 'Use plural form for multiple items',
            'grammar_preposition': 'Use correct preposition (to, at, in, on, etc.)',
            'grammar_gerund_infinitive': 'Use gerund (-ing) or infinitive (to + verb) correctly',
            'vocabulary_word_form': 'Use correct word form (adjective, noun, verb, adverb)',
            'grammar_sentence_structure': 'Use correct sentence structure (subject + verb + object)',
            'grammar_general': 'Follow standard English grammar rules'
        }
        return rules.get(mistake_type, 'Check grammar and usage')
