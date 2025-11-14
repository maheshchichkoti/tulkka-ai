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
        ]
    
    def extract(self, transcript: str) -> List[Dict[str, str]]:
        """Extract mistakes and corrections from transcript"""
        mistakes = []
        seen = set()
        
        # Extract explicit corrections
        for pattern in self.correction_patterns:
            for match in re.finditer(pattern, transcript, re.IGNORECASE):
                incorrect = match.group(1).strip()
                correct = match.group(2).strip()
                key = (incorrect.lower(), correct.lower())
                if key not in seen:
                    mistakes.append({
                        'incorrect': incorrect,
                        'correct': correct,
                        'type': 'explicit_correction',
                        'context': match.group(0)
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
        
        return mistakes[:10]  # Return top 10
