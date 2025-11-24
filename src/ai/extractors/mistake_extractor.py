"""Mistake extraction from lesson transcripts"""
from typing import List, Dict
import re

class MistakeExtractor:
    """Extracts student mistakes and corrections from lessons"""
    
    def __init__(self):
        self.correction_patterns = [
            r"not\s+['\"]([^'\"]+)['\"]\s*,?\s*(?:it's|say|use)\s+['\"]([^'\"]+)['\"]",
            r"don't say\s+['\"]([^'\"]+)['\"]\s*,?\s*say\s+['\"]([^'\"]+)['\"]",
            r"instead of\s+['\"]([^'\"]+)['\"]\s*,?\s*(?:use|say)\s+['\"]([^'\"]+)['\"]",
            r"(?:incorrect|wrong|mistake):\s*['\"]([^'\"]+)['\"]\s*(?:correct|right):\s*['\"]([^'\"]+)['\"]",
            r"should\s+be\s+['\"]([^'\"]+)['\"]",
            r"should\s+say\s+['\"]([^'\"]+)['\"]",
            r"should\s+use\s+['\"]([^'\"]+)['\"]",
            r"should\s+have\s+['\"]([^'\"]+)['\"]",
            r"should\s+not\s+have\s+['\"]([^'\"]+)['\"]",
            r"should\s+be\s+['\"]([^'\"]+)['\"]\s*,?\s*instead\s+of\s+['\"]([^'\"]+)['\"]",
        ]
    
    def extract(self, transcript: str) -> List[Dict[str, str]]:
        """Extract mistakes and corrections from transcript"""
        mistakes = []
        seen = set()
        
        # Split transcript into lines for context
        lines = transcript.split('\n')
        
        # Extract explicit corrections with context
        for i, line in enumerate(lines):
            # Look for teacher corrections
            if re.search(r'Teacher:', line, re.IGNORECASE):
                # Check if previous line was student speaking
                student_line = lines[i-1] if i > 0 and re.search(r'Student:', lines[i-1], re.IGNORECASE) else None
                
                for pattern in self.correction_patterns:
                    for match in re.finditer(pattern, line, re.IGNORECASE):
                        groups = match.groups()
                        if len(groups) == 1:
                            # Single group = correction only
                            correct = groups[0].strip()
                            # Try to extract incorrect from student line
                            if student_line:
                                student_text = re.sub(r'Student:\s*', '', student_line, flags=re.IGNORECASE).strip()
                                incorrect = student_text
                            else:
                                continue
                        else:
                            # Two groups = incorrect and correct
                            incorrect = groups[0].strip()
                            correct = groups[1].strip()
                        
                        key = (incorrect.lower(), correct.lower())
                        if key not in seen and incorrect and correct:
                            # Categorize mistake type
                            mistake_type = self._categorize_mistake(incorrect, correct)
                            mistakes.append({
                                'incorrect': incorrect,
                                'correct': correct,
                                'type': mistake_type,
                                'context': match.group(0),
                                'rule': self._get_grammar_rule(incorrect, correct, mistake_type)
                            })
                            seen.add(key)
        
        # Extract grammar mistakes (common patterns)
        grammar_patterns = [
            (r'\b(have|has)\s+to\s+(\w+ed)\b', 'modal_verb_error'),
            (r'\b(is|are|was|were)\s+(\w+ing)\b', 'tense_error'),
            (r'\b(a|an)\s+([aeiou]\w+)\b', 'article_error'),
        ]
        
        for pattern, error_type in grammar_patterns:
            for match in re.finditer(pattern, transcript, re.IGNORECASE):
                context = match.group(0)
                if context.lower() not in seen:
                    mistakes.append({
                        'incorrect': context,
                        'correct': '',  # Would need AI to suggest
                        'type': error_type,
                        'context': context
                    })
                    seen.add(context.lower())
        
        return mistakes[:15]  # Return top 15 mistakes
    
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
    
    def _get_grammar_rule(self, incorrect: str, correct: str, mistake_type: str) -> str:
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
