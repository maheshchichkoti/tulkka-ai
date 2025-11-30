# src/ai/generators.py
"""
High-quality rule-based generators for Tulkka.

Goals:
- Provide pedagogically-sound items (flashcards, spelling, fill_blank, sentence_builder,
  grammar_challenge, advanced_cloze) without any LLM dependency.
- Add metadata fields: difficulty, source, hint, explanation, concept.
- Produce stable, varied, and meaningful distractors using linguistically-aware rules.
"""

from __future__ import annotations
import uuid
import random
import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)
random.seed(1337)  # deterministic unless caller reseeds

# Optional translator (fallback to empty translations if not available)
try:
    from deep_translator import GoogleTranslator
    def _translator(target="he"):
        lang = "iw" if target.lower() == "he" else target
        try:
            return GoogleTranslator(source="en", target=lang)
        except Exception:
            return None
except Exception:
    GoogleTranslator = None
    def _translator(target="he"):
        return None

def _tr(text: str, t):
    if not text or not t:
        return ""
    try:
        return t.translate(text)
    except Exception:
        return ""

# -------------------------
# Helpers: difficulty, cleanup
# -------------------------
COMMON_WORDS = {
    # small set to treat as beginner (extend as needed)
    "open", "close", "name", "please", "camera", "hello", "thank", "fine", "great", "eat", "go", "have", "is", "are"
}

def _assess_difficulty(word_or_sentence: str) -> str:
    s = (word_or_sentence or "").strip()
    if not s:
        return "beginner"
    tokens = s.split()
    avg_len = sum(len(t) for t in tokens) / max(1, len(tokens))
    if len(tokens) == 1:
        w = tokens[0].lower()
        if w in COMMON_WORDS or len(w) <= 4:
            return "beginner"
        if len(w) <= 7:
            return "intermediate"
        return "advanced"
    else:
        if avg_len < 4:
            return "beginner"
        if avg_len < 6:
            return "intermediate"
        return "advanced"

def _clean_sentence_for_example(sent: str) -> str:
    if not sent:
        return ""
    s = sent.strip()
    # remove speaker tokens like "Khadija:" at start
    s = re.sub(r'^[A-Za-z]+[:\-]\s*', '', s)
    # normalize spaces and trailing fragments
    s = re.sub(r'\s+', ' ', s)
    s = s.strip(' \n\t"\'')
    # Ensure sentence ends with punctuation
    if not re.search(r'[.!?]$', s):
        s = s + '.'
    return s

def _pick_example_sentence(word: str, transcript: str) -> str:
    if not transcript:
        return ""
    # split into candidate sentences and pick the shortest that contains the word
    parts = re.split(r'(?<=[.!?])\s+', transcript)
    word_l = word.lower()
    candidates = [p.strip() for p in parts if word_l in p.lower()]
    if not candidates:
        # fallback: return first non-empty cleaned sentence
        for p in parts:
            t = p.strip()
            if len(t.split()) >= 3:
                return _clean_sentence_for_example(t)
        return ""
    # prefer short and clear sentences
    candidates.sort(key=lambda x: (len(x.split()), len(x)))
    return _clean_sentence_for_example(candidates[0])

# -------------------------
# Lexical distractor helpers
# -------------------------
def _pluralize(noun: str) -> str:
    # simple plural rules (not exhaustive)
    if noun.endswith('y') and not noun.endswith(('ay','ey','iy','oy','uy')):
        return noun[:-1] + 'ies'
    if noun.endswith(('s','x','z','ch','sh')):
        return noun + 'es'
    return noun + 's'

def _to_ing(verb: str) -> str:
    # naive -ing form
    if len(verb) <= 2:
        return verb + 'ing'
    if verb.endswith('e') and not verb.endswith('ee'):
        return verb[:-1] + 'ing'
    if re.match(r'.*[^aeiou][aeiou][^aeiou]$', verb):
        return verb + verb[-1] + 'ing'  # double consonant
    return verb + 'ing'

def _to_past(verb: str) -> str:
    if verb.endswith('e'):
        return verb + 'd'
    if verb.endswith('y') and verb[-2] not in 'aeiou':
        return verb[:-1] + 'ied'
    return verb + 'ed'

def _common_misspelling(word: str) -> str:
    # simple heuristics: swap two internal adjacent letters or drop a letter
    if len(word) <= 3:
        return word + word[-1]
    i = min(2, max(1, len(word)//3))
    arr = list(word)
    arr[i], arr[i+1 if i+1 < len(arr) else i] = arr[i+1 if i+1 < len(arr) else i], arr[i]
    swapped = ''.join(arr)
    if swapped.lower() != word.lower():
        return swapped
    return word[:-1]  # drop last as fallback

def _unique_keep_first(items: List[str]) -> List[str]:
    out = []
    seen = set()
    for x in items:
        k = (x or "").strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out

# -------------------------
# High-quality option generator (ensures 4 options)
# -------------------------
def _build_options_for_target(target: str, concept_hint: Optional[str] = None) -> List[str]:
    """
    Create 4 plausible options including target.
    concept_hint can guide the pattern (e.g. 'verb_third_person', 'plural', 'article', 'preposition').
    """
    opts = [target]
    t = target.strip()

    # If target looks like a single verb token:
    if re.match(r"^[A-Za-z']+$", t) and ' ' not in t:
        # verb forms
        opts_candidates = []
        opts_candidates.append(_to_ing(t))
        opts_candidates.append(_to_past(t))
        opts_candidates.append(t + 's' if not t.endswith('s') else t[:-1])  # simple 3rd person or remove
        opts_candidates.append(_common_misspelling(t))
        opts_candidates.append(t.capitalize())
        opts_candidates = [o for o in opts_candidates if o and o.lower() != t.lower()]
        opts.extend(opts_candidates)
    else:
        # multiword or noun -> try plurals, removing punctuation
        base = re.sub(r'[^\w\s]', '', t)
        words = base.split()
        if len(words) == 1:
            w = words[0]
            opts_candidates = [_pluralize(w), _common_misspelling(w), w + 's', w.capitalize()]
            opts.extend(opts_candidates)
        else:
            # choose variations on one word in the phrase (prefer first content word)
            content = next((w for w in words if len(w) > 3), words[0])
            opts_candidates = [
                base.replace(content, _pluralize(content)),
                base.replace(content, _to_ing(content)),
                base.replace(content, _common_misspelling(content)),
                base.replace(content, content.capitalize())
            ]
            opts.extend(opts_candidates)

    # Add grammatical confusions for specific concept hints
    if concept_hint:
        if concept_hint == 'third_person':
            # Provide base / -s / -ing / common misspell
            opts = [target, target.rstrip('s'), target + 's' if not target.endswith('s') else target, _to_ing(target), _common_misspelling(target)]
        if concept_hint == 'article':
            # If target is like "a cat" suggest "an cat", "the cat", "cat"
            words = t.split()
            if words:
                noun = ' '.join(words[1:]) if words[0].lower() in ('a','an','the') else ' '.join(words)
                opts = [target, f"the {noun}", f"a {noun}", f"an {noun}", noun]
        if concept_hint == 'preposition':
            # swap common prepositions
            swaps = ['to','at','in','on','for','with','about']
            if len(t.split()) >= 3:
                parts = t.split()
                # replace preposition (assume middle token) with alternatives
                idx = min(2, len(parts)-2)
                noun = parts[idx+1]
                candidates = [f"{' '.join(parts[:idx])} {p} {noun}" for p in swaps]
                opts = [target] + candidates

    opts = _unique_keep_first(opts)
    # ensure target included and at front
    if target not in opts:
        opts.insert(0, target)
    # truncate / pad with sensible variants
    final = []
    for o in opts:
        if len(final) >= 4:
            break
        final.append(o)
    # pad if needed with simple morphological variants
    i = 0
    while len(final) < 4:
        cand = (target + str(i))[:20]
        final.append(cand)
        i += 1

    random.shuffle(final)
    # ensure target present
    if target not in final:
        final[0] = target
    return final

# -------------------------
# Generator implementations
# -------------------------

def generate_flashcards(vocab: List[Dict[str, Any]], transcript: str, *, limit: int = 8) -> List[Dict[str, Any]]:
    """
    vocab: list of dicts or simple strings. Expected keys: 'word', 'context', 'example_sentence', etc.
    Returns list of flashcard dicts with fields:
    id, word, translation, example_sentence, difficulty, source, hint
    """
    t = _translator("he")
    out = []
    cnt = 0
    for v in (vocab or []):
        if cnt >= limit:
            break
        if isinstance(v, dict):
            word = (v.get("word") or v.get("text") or "").strip()
            example = v.get("example_sentence") or v.get("context") or ""
            source = v.get("category") or "vocabulary_extractor"
        else:
            word = str(v).strip()
            example = ""
            source = "vocabulary_extractor"
        if not word:
            continue
        # build example sentence if empty
        example_clean = _clean_sentence_for_example(example) if example else _pick_example_sentence(word, transcript)
        translation = _tr(word, t)
        difficulty = _assess_difficulty(word)
        hint = f"Word from lesson ({source})"
        out.append({
            "id": str(uuid.uuid4()),
            "word": word,
            "translation": translation,
            "example_sentence": example_clean,
            "difficulty": difficulty,
            "source": source,
            "hint": hint,
        })
        cnt += 1
    return out

def generate_spelling_items(vocab: List[Dict[str, Any]], transcript: str, *, limit: int = 8) -> List[Dict[str, Any]]:
    """
    Returns spelling items: id, word, translation, hint, difficulty, source
    Hint should help the student (e.g., syllable count / translation).
    """
    t = _translator("he")
    out = []
    cnt = 0
    for v in (vocab or []):
        if cnt >= limit:
            break
        if isinstance(v, dict):
            word = (v.get("word") or v.get("text") or "").strip()
            source = v.get("category") or "vocabulary_extractor"
        else:
            word = str(v).strip()
            source = "vocabulary_extractor"
        if not word:
            continue
        translation = _tr(word, t)
        # hint: give syllable-ish clue or translation fallback
        syllables = max(1, len(re.findall(r'[aeiouy]+', word.lower())))
        hint_words = []
        if translation:
            hint_words.append(translation)
        hint_words.append(f"{syllables} syllable{'s' if syllables>1 else ''}")
        hint = " • ".join(hint_words)
        difficulty = _assess_difficulty(word)
        out.append({
            "id": str(uuid.uuid4()),
            "word": word,
            "translation": translation,
            "hint": hint,
            "difficulty": difficulty,
            "source": source,
        })
        cnt += 1
    return out

def generate_fill_blank(mistakes: List[Dict[str, Any]], transcript: str, *, limit: int = 8) -> List[Dict[str, Any]]:
    """
    Creates fill-in-the-blank items using mistakes/corrections or sentences.
    Fields: id, sentence, options (4), correct_answer, difficulty, source_mistake, explanation, hint
    """
    out = []
    cnt = 0
    # prefer explicit mistakes with 'correct' or 'corrected' keys
    for m in (mistakes or []):
        if cnt >= limit:
            break
        # support several shapes
        correct = m.get("correct") or m.get("corrected") or m.get("fix") or m.get("suggestion") or ""
        raw = m.get("incorrect") or m.get("raw") or ""
        context = m.get("context") or ""
        if not correct and not raw:
            continue
        # use correct as the answer if present; otherwise try to pick a target token from raw
        target = correct.strip() or (raw.split()[0] if raw else "")
        if not target:
            continue
        # build a sentence: prefer context, otherwise pick from transcript
        sentence_source = context or _pick_example_sentence(target, transcript) or raw or ""
        sentence = sentence_source.replace(target, "_____") if target in sentence_source else "_____ " + sentence_source
        # concept hint: try to detect grammar concept from rule/type
        typ = (m.get("type") or "").lower()
        if "verb" in typ:
            concept = "verb_tense"
            concept_hint = "verb_forms"
        elif "article" in typ:
            concept = "article"
            concept_hint = "article"
        elif "preposition" in typ:
            concept = "preposition"
            concept_hint = "preposition"
        elif "plural" in typ:
            concept = "plural"
            concept_hint = "plural"
        else:
            concept = "general"
            concept_hint = None
        options = _build_options_for_target(target, concept_hint)
        explanation = m.get("rule") or f"Correct form: {target}."
        hint = "Choose the grammatically correct option."
        difficulty = _assess_difficulty(target if target else sentence)
        out.append({
            "id": str(uuid.uuid4()),
            "sentence": sentence,
            "options": options,
            "correct_answer": target,
            "difficulty": difficulty,
            "source_mistake": raw or context,
            "explanation": explanation,
            "hint": hint,
            "concept": concept
        })
        cnt += 1

    # If not enough fill blanks from mistakes, generate from sentences in transcript
    if cnt < limit:
        # try to create blanks from sentences in transcript
        parts = re.split(r'(?<=[.!?])\s+', transcript or "")
        for p in parts:
            if cnt >= limit:
                break
            s = p.strip()
            if not s:
                continue
            # pick a mid-token candidate (noun or verb)
            tokens = [t for t in re.findall(r"[A-Za-z']+", s) if len(t) > 2]
            if not tokens:
                continue
            mid = tokens[len(tokens)//2]
            if len(mid) <= 2:
                continue
            sentence = s.replace(mid, "_____", 1)
            options = _build_options_for_target(mid)
            out.append({
                "id": str(uuid.uuid4()),
                "sentence": _clean_sentence_for_example(sentence),
                "options": options,
                "correct_answer": mid,
                "difficulty": _assess_difficulty(s),
                "source_mistake": "auto_sentence",
                "explanation": f"Correct: {mid}",
                "hint": "Choose the word that best fits the sentence.",
                "concept": "vocab_cloze"
            })
            cnt += 1

    return out[:limit]

def generate_sentence_builder(sentences: List[Dict[str, Any]], *, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Build sentence reconstruction items. Each item:
    id, english, tokens, accepted (list of token sequences), translation, hint, difficulty
    Accepts sentence dicts or strings.
    """
    t = _translator("he")
    out = []
    cnt = 0
    for s in (sentences or []):
        if cnt >= limit:
            break
        if isinstance(s, dict):
            sent = s.get("sentence") or s.get("text") or s.get("english_sentence") or ""
        else:
            sent = str(s)
        sent = sent.strip()
        if not sent:
            continue
        clean = _clean_sentence_for_example(sent)
        tokens = re.findall(r"[A-Za-z']+|[,\.!?;:]", clean)
        # create accepted sequences (single canonical)
        accepted = [tokens]
        translation = _tr(clean, t) if t else ""
        hint = "Rebuild the sentence in the correct order."
        difficulty = _assess_difficulty(clean)
        out.append({
            "id": str(uuid.uuid4()),
            "english": clean,
            "tokens": tokens,
            "accepted": accepted,
            "translation": translation,
            "hint": hint,
            "difficulty": difficulty,
        })
        cnt += 1
    return out

def generate_grammar_challenge(mistakes: List[Dict[str, Any]], *, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Generate MCQ grammar prompts from mistakes or sentence patterns.
    Fields: id, prompt, options, correct_answer, explanation, hint, difficulty, concept
    """
    out = []
    cnt = 0
    # Use explicit mistakes first
    for m in (mistakes or []):
        if cnt >= limit:
            break
        correct = m.get("correct") or m.get("corrected") or m.get("fix") or ""
        raw = m.get("incorrect") or m.get("raw") or ""
        context = m.get("context") or ""
        if not correct:
            continue
        # build prompt favoring a short phrase
        # attempt format: "She _____ every day."
        # If the correct target is a verb, replace in a small sentence
        prompt_sentence = context or _pick_example_sentence(correct, raw or "")
        if not prompt_sentence:
            prompt_sentence = f"_____ {correct}." if len(correct.split())>1 else f"_____ to school every day."
        # choose a single target token for the MCQ
        target_token = correct.split()[0]
        # concept detection
        typ = (m.get("type") or "").lower()
        if "verb" in typ:
            concept = "verb_tense"
            hint_concept = "third_person" if 's' in target_token or len(target_token)>1 else "verb_forms"
        elif "article" in typ:
            concept = "article"
            hint_concept = "article"
        elif "preposition" in typ:
            concept = "preposition"
            hint_concept = "preposition"
        else:
            concept = "grammar_general"
            hint_concept = None
        options = _build_options_for_target(target_token, hint_concept)
        explanation = m.get("rule") or f"Correct form: {target_token}."
        difficulty = _assess_difficulty(target_token)
        out.append({
            "id": str(uuid.uuid4()),
            "prompt": prompt_sentence.replace(target_token, "_____") if target_token in prompt_sentence else prompt_sentence,
            "options": options,
            "correct_answer": target_token,
            "explanation": explanation,
            "hint": "Choose the correct grammar form.",
            "difficulty": difficulty,
            "concept": concept,
            "source_mistake": raw or context
        })
        cnt += 1

    # If not enough, heuristically create grammar items (subject-verb agreement, articles)
    if cnt < limit:
        # subject-verb agreement items
        templates = [
            ("She ____ to school every day.", "goes", "third_person"),
            ("They ____ the book every week.", "read", "verb_forms"),
            ("I ____ an apple for breakfast.", "eat", "verb_forms"),
            ("He ____ a doctor.", "is", "be_verb"),
            ("We ____ to the park.", "go", "verb_forms"),
        ]
        random.shuffle(templates)
        for tpl in templates:
            if cnt >= limit:
                break
            prompt, target_token, hint_concept = tpl
            options = _build_options_for_target(target_token, hint_concept)
            explanation = f"Correct form is '{target_token}'."
            out.append({
                "id": str(uuid.uuid4()),
                "prompt": prompt,
                "options": options,
                "correct_answer": target_token,
                "explanation": explanation,
                "hint": "Select the correct word for the sentence.",
                "difficulty": _assess_difficulty(target_token),
                "concept": hint_concept,
                "source_mistake": "auto_template"
            })
            cnt += 1

    return out[:limit]

def generate_advanced_cloze(sentences: List[Dict[str, Any]], *, limit: int = 2) -> List[Dict[str, Any]]:
    """
    Produce advanced cloze items with two blanks each. Each blank: options (4), correct, hint
    Fields: id, sentence, blank1, blank2, difficulty, source_sentence, concept
    """
    out = []
    cnt = 0
    for s in (sentences or []):
        if cnt >= limit:
            break
        if isinstance(s, dict):
            sent = s.get("sentence") or s.get("text") or s.get("english_sentence") or ""
        else:
            sent = str(s)
        sent = _clean_sentence_for_example(sent)
        words = re.findall(r"[A-Za-z']+", sent)
        if len(words) < 6:
            continue
        # pick two content words not first/last
        candidates = [w for w in words[1:-1] if len(w) > 2]
        if len(candidates) < 2:
            continue
        # pick spaced words
        w1 = candidates[0]
        w2 = candidates[min(2, len(candidates)-1)]
        # ensure different
        if w1.lower() == w2.lower():
            continue
        cloze_sent = sent.replace(w1, "_____", 1).replace(w2, "_____", 1)
        options1 = _build_options_for_target(w1)
        options2 = _build_options_for_target(w2)
        out.append({
            "id": str(uuid.uuid4()),
            "sentence": cloze_sent,
            "blank1": {
                "options": options1,
                "correct": w1,
                "hint": "Consider the grammar and meaning of blank 1."
            },
            "blank2": {
                "options": options2,
                "correct": w2,
                "hint": "Consider the grammar and meaning of blank 2."
            },
            "difficulty": _assess_difficulty(sent),
            "source_sentence": sent,
            "concept": "advanced_cloze"
        })
        cnt += 1
    return out[:limit]

# -------------------------
# Backward-compatible aliases
# -------------------------
def generate_cloze(mistakes, transcript, *, limit=8):
    return generate_fill_blank(mistakes, transcript, limit=limit)

def generate_grammar(mistakes, *, limit=3):
    return generate_grammar_challenge(mistakes, limit=limit)

def generate_sentence_items(sentences, *, limit=3):
    return generate_sentence_builder(sentences, limit=limit)
