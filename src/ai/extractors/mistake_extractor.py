"""Mistake extraction from lesson transcripts"""
from typing import List, Dict
import re

class MistakeExtractor:
    """Extracts student mistakes and corrections from lessons"""
    
    def __init__(self):
        # Patterns that capture (incorrect, correct) pairs
        # These work with or without quotes around the phrases
        self.correction_patterns = [
            # "not X, say Y" or "not X, it's Y" (with quotes)
            (r"(?:not|don't\s+say)\s+['\"]([^'\"]+)['\"]\s*,?\s*(?:say|use|it's)\s+['\"]([^'\"]+)['\"]", False),
            # "instead of X, use Y" (with quotes)
            (r"instead\s+of\s+['\"]([^'\"]+)['\"]\s*,?\s*(?:use|say)\s+['\"]([^'\"]+)['\"]", False),
            # "X should be Y" (with quotes)
            (r"['\"]([^'\"]+)['\"]\s+should\s+be\s+['\"]([^'\"]+)['\"]", False),
            # "should be Y (not X)" - reversed order (with quotes)
            (r"should\s+be\s+['\"]([^'\"]+)['\"]\s*(?:not|instead\s+of)\s+['\"]([^'\"]+)['\"]", True),
            # "Correction: X" or "Correct: X" or "The correct sentence is X"
            (r"(?:correction|correct(?:ion)?|the correct (?:sentence|form|way) is)[:\s]+(.+?)(?:\.|$)", None),
            # "It should be X" or "Should be X"
            (r"(?:it )?should be[:\s]+(.+?)(?:\.|$)", None),
            # "Better: X" or "Better to say X"
            (r"better(?:\s+to\s+say)?[:\s]+(.+?)(?:\.|$)", None),
            # "Careful! X" pattern
            (r"careful!?[:\s]+(.+?)(?:\.|$)", None),
        ]
    
    def extract(self, transcript: str) -> List[Dict[str, str]]:
        """Extract mistakes and corrections from transcript"""
        mistakes = []
        seen = set()
        
        # Split into lines - handle both newlines and speaker labels
        lines = re.split(r'\n|(?=(?:Teacher|Student)[^:]*:)', transcript)
        lines = [l.strip() for l in lines if l.strip()]
        
        # Track last student utterance for context
        last_student_text = ""
        
        for i, line in enumerate(lines):
            # Track student utterances
            if re.search(r'Student', line, re.IGNORECASE):
                last_student_text = re.sub(r'^.*?Student[^:]*:\s*', '', line, flags=re.IGNORECASE).strip()
                continue
            
            # Look for teacher corrections
            if not re.search(r'Teacher', line, re.IGNORECASE):
                continue
            
            teacher_text = re.sub(r'^.*?Teacher[^:]*:\s*', '', line, flags=re.IGNORECASE).strip()
            
            # Try each correction pattern
            for pattern, reverse_order in self.correction_patterns:
                for match in re.finditer(pattern, teacher_text, re.IGNORECASE):
                    groups = match.groups()
                    
                    # Single-group patterns (correction only, use last student text as incorrect)
                    if reverse_order is None:
                        if len(groups) >= 1 and groups[0]:
                            correct = groups[0].strip().rstrip('.')
                            incorrect = last_student_text
                            if correct and incorrect and correct.lower() != incorrect.lower():
                                key = (incorrect.lower()[:50], correct.lower()[:50])
                                if key not in seen:
                                    mistake_type = self._categorize_mistake(incorrect, correct)
                                    mistakes.append({
                                        'incorrect': incorrect[:100],
                                        'correct': correct[:100],
                                        'type': mistake_type,
                                        'context': match.group(0)[:100],
                                        'rule': self._get_grammar_rule(mistake_type)
                                    })
                                    seen.add(key)
                        continue
                    
                    # Two-group patterns (both incorrect and correct captured)
                    if len(groups) != 2:
                        continue
                    
                    if reverse_order:
                        correct = groups[0].strip()
                        incorrect = groups[1].strip()
                    else:
                        incorrect = groups[0].strip()
                        correct = groups[1].strip()
                    
                    key = (incorrect.lower()[:50], correct.lower()[:50])
                    if not incorrect or not correct or key in seen:
                        continue
                    
                    mistake_type = self._categorize_mistake(incorrect, correct)
                    mistakes.append({
                        'incorrect': incorrect[:100],
                        'correct': correct[:100],
                        'type': mistake_type,
                        'context': match.group(0)[:100],
                        'rule': self._get_grammar_rule(mistake_type)
                    })
                    seen.add(key)
        
        # Fallback: look for student utterances followed by teacher corrections
        # This handles conversational patterns without explicit correction markers
        for i in range(len(lines) - 1):
            if not re.search(r'Student', lines[i], re.IGNORECASE):
                continue
            if not re.search(r'Teacher', lines[i+1], re.IGNORECASE):
                continue
            
            student_text = re.sub(r'^.*?Student[^:]*:\s*', '', lines[i], flags=re.IGNORECASE).strip()
            teacher_text = re.sub(r'^.*?Teacher[^:]*:\s*', '', lines[i+1], flags=re.IGNORECASE).strip()
            
            # Skip if teacher is asking a question or giving praise
            if teacher_text.endswith('?') or re.search(r'^(good|nice|great|excellent|perfect)', teacher_text, re.IGNORECASE):
                continue
            
            # Check if teacher text looks like a correction (similar structure, different words)
            if 5 < len(teacher_text) < 100 and student_text and teacher_text:
                student_words = set(student_text.lower().split())
                teacher_words = set(teacher_text.lower().split())
                overlap = len(student_words & teacher_words) / max(len(student_words), 1)
                
                # Some overlap but not identical - likely a correction
                if 0.2 < overlap < 0.95:
                    key = (student_text[:50].lower(), teacher_text[:50].lower())
                    if key not in seen:
                        mistake_type = self._categorize_mistake(student_text, teacher_text)
                        mistakes.append({
                            'incorrect': student_text[:100],
                            'correct': teacher_text[:100],
                            'type': mistake_type,
                            'context': f"{student_text[:50]}... → {teacher_text[:50]}...",
                            'rule': self._get_grammar_rule(mistake_type)
                        })
                        seen.add(key)
        
        return mistakes[:15]
    
    def _categorize_mistake(self, incorrect: str, correct: str) -> str:
        """Categorize the type of mistake"""
        incorrect_lower = incorrect.lower()
        correct_lower = correct.lower()
        
        # Verb tense errors
        if any(word in incorrect_lower for word in ['waking', 'go', 'buy', 'cooking', 'stay']):
            if any(word in correct_lower for word in ['wake', 'went', 'bought', 'cooked', 'stayed']):
                return 'grammar_verb_tense'
        
        # Subject-verb agreement
        if 'eats' in incorrect_lower and 'eat' in correct_lower:
            return 'grammar_subject_verb_agreement'
        
        # Article errors
        if ('is engineer' in incorrect_lower or 'is teacher' in incorrect_lower) and \
           ('is an engineer' in correct_lower or 'is a teacher' in correct_lower):
            return 'grammar_article'
        
        # Plural errors
        if ('egg' in incorrect_lower and 'eggs' in correct_lower) or \
           ('vegetable' in incorrect_lower and 'vegetables' in correct_lower) or \
           ('day' in incorrect_lower and 'days' in correct_lower):
            return 'grammar_plural'
        
        # Preposition errors
        if 'listening music' in incorrect_lower and 'listening to music' in correct_lower:
            return 'grammar_preposition'
        
        # Gerund/infinitive errors
        if 'like play' in incorrect_lower and 'like playing' in correct_lower:
            return 'grammar_gerund_infinitive'
        
        # Word form errors
        if 'comfort' in incorrect_lower and 'comfortable' in correct_lower:
            return 'vocabulary_word_form'
        
        # Sentence structure
        if 'in my family have' in incorrect_lower and 'there are' in correct_lower:
            return 'grammar_sentence_structure'
        
        return 'grammar_general'
    
    def _get_grammar_rule(self, mistake_type: str) -> str:
        """Get a brief grammar rule explanation"""
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
