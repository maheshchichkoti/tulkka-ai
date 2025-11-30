# src/ai/generators/__init__.py
from .flashcards_generator import generate_flashcards
from .spelling_generator import generate_spelling_items
from .fill_blank_generator import generate_fill_blank
from .sentence_builder_generator import generate_sentence_builder
from .grammar_generator import generate_grammar_challenge
from .advanced_cloze_generator import generate_advanced_cloze

# Backward-compatible aliases (older code may call these)
def generate_cloze(mistakes, transcript, *, limit=8):
    return generate_fill_blank(mistakes, transcript, limit=limit)

def generate_grammar(mistakes, *, limit=3):
    return generate_grammar_challenge(mistakes, limit=limit)

def generate_sentence_items(sentences, *, limit=3):
    return generate_sentence_builder(sentences, limit=limit)
