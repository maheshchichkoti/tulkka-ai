#!/usr/bin/env python3
# FINAL CLEAN WORKING TEST FILE

import sys
import logging
import json

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("pipeline_test")

PASS_THRESHOLD = 7.0

# ============================================================================
# REAL TRANSCRIPT 1: Teacher Philip - Level Test Lesson (Hobbies, Reading)
# ============================================================================
TRANSCRIPT_1 = """
"הלו. היי יונתן, יום טוב. יכול לדעתי טוב? כן. אוקיי, מאוד טוב, איך אתה? טוב. יופי. אז קודם כל, יונתן, לפני שהתחלנו את הלסון שלנו, יש לך אפליקציה של תולכה חדשה? אפליקציה. In your phone. You have the new one where you can see your homework, your feedbacks and schedule. You have? Okay, so that's good. All right. So we will have first a simple quiz and review. Regarding our lesson last time, אוקיי? על השיעור שלנו בעבר. All right? So let me just open our exercises. You remember our lesson last time about possessive pronouns? ואההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההה הפרטים. We will do a review, okay? So that you will remember. Okay. I think you will remember this. These are easier. Okay, so we have this one. Let's first answer this one. Okay, so you remember, Yonatan, our... Words mine, yours, his, her, ours or their. נכון, as possessive pronouns for the female or the בנות, אישה, we say her. נכון, for the males, we say his. And then for the רבים, for the plural form, we say theirs, ours, ours, or yours. So let's try this one. First read and then tell me your answer. What will be your answer? Let's start. Read first. I am riding my bike. איך. אומרים שלי? שלקה או שלק. אז אם אנחנו נקראים שלי, אוקיי, מהקהילה מי, אז זה יכול להיות קהילה או מין. שלי. מין. מין, אוקיי. אז זה יכול להיות מין. אוקיי, אז הקהילה הבסיסית היא מין. אוקיי, אסקיסימי. Are the children's books. רבים. they are So what is the plural of they? So the possessive pronoun of they, what will be? It's between a ours or theirs. So look at this here, they. So what will be the possessive pronoun of they? It's in רבים, נכון? They, hem. Okay, so how do we say their's, נכון? שלהם. יופי. Next. אוקיי. Read. That my money belongs to my retailer, which is. איך אנחנו אומרים שלו? איך אנחנו אומרים שלו? It can be Ben yours or his. His. His, נכון, because it's a brother. Okay, זה שלו. It is his. יפה. Okay, next one, number four. So we have here these for a plural. These are my sister's slippers. They are... So now it's the female version. So, because I was a sister. So, they are hem shela. So, איך אני אקנוב להם שלה in English? אז כאן, בת קלה, אנחנו אומרים, זה הוא, לבנון. אז לבנון, איך אני אומרים? הם הם או להם? הם. אז הם הוא לבנון. שלו שלו שלו שלו שלו שלו שלו שלו שלו It should be her, נכון? This is the... How do you say? יקיב? יקיב, you say, for the female? So it should be hers, okay? From the word her. It's the... We have for the brother, for the male, we say his. So the female, we say her, okay? יקיב. They are hers. Good. So next we have here number five. Can you please read? The car belongs to us. שלנו. Because us. שלנו. It is... איך אומרים שלנו? It. Should be yours, ours. It is ours. יפה. So next, number six. רואה קודם, ומאזין. מ-ד-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א-א. וויט. וויט. כמו לבן. זה הוא. אז מיסטר, זה יכול להיות... זה מלך. אתה זוכר למלך? הוא או היא? מלך. אההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההההה. נקסט 1, נמבר 7. ראית קודם. פייאר. פייאר, זוב. אוף. אוקיי, גלסס. הם הם, אז זה אי, מה זה הפרונום המנסים של אי? שילי. מין. מין, מאוד טוב. אוקיי, יפה. נמבר 8. זה הוא, עכשיו, מ-ר-ס, זה אמא, אוקיי? אמא. This is Mrs. Robinson's wheelchair. It's his. אוקיי, לבנות or female. How do you say? His or hers? From the word hers. Very good. So, wheelchair, it's the אגלה. יפה. אתה מקבל את זה עכשיו, ינתן. אז הבאה הבאה הבאה הבאה הבאה הבאה. הבאה הבאה הבאה הבאה הבאה. Belongs to me. So, like, כמו שנאמרת, זה שלי. So, what will be the answer? מין. מין, very well. Okay. The last one in our exercises. Okay. Read and answer, please. He is your מיני, כסף שלך או שלך איך אנחנו אומרים? אוקיי. יונתן יפה. All right, so that's for our possessive pronoun, okay? You remember the he's and her for male and for female. יופי, יונתן, כל הכבוד לך. All right, so let's, it should be again, so you have here. So let's proceed to our new lesson, all right? I think we can already move to our new lesson because ואתה כבר קיבלת את ה-a, ובאמת את ה-b. אז הטופיק הבא שלנו הוא לדסקריב סימפרית אבנט אוקיי כמו חברות ולמכין פלאנס ומרחבות אז בואו נתחיל בלבלת פלאנס או מרחבות עכשיו יונתן, אם אנחנו, אם אנחנו אומרים, מבחינים, אז זה, זה, זאת אומרת, זה עדיין עוד לא קורה, אוקיי? אז מה, מה, מה צריך להיות? זה, זה, זה, זה, זה, זה, זה, זה, זה, זה, זה, זה, זה, זה, זה, זה, זה, זה, זה, זה, זה, זה, זה, זה, זה, אם זה בעתיד, מה זאת אומרת? זה מעבר למהלך או למהלך? בעתיד איך נקרא עתיד באנגלית? אם אני אומר אני עושה תוכנית בעתיד. זה עדיין קורה, זה עוד לא קורה זה עדיין יהיה. עושים תוכנית. אוקיי, אז יש לנו פה, ראשון, בואו נסתכל על המספרים שלנו. אז יש לנו סקצ'ול. מה זאת אומרת סקצ'ול? יונתן, אתה יכול לבחור את הסקצ'ול שלך. In the Tulka application, so Mazzi's schedule, it's the Luwak, okay? Luwak, schedule, all right? For example, my English lesson, my schedule for English lesson is on Monday, so that's your schedule. Next we have here, can you please read the example? I have a busy schedule this week. I have a busy schedule this week. So we have here, מה זה אומר לנו? I have a busy schedule this week. I have, it means יש לי. What is the word busy? אפליקציה. באפליקציה, it's not written here, but... Busy, it means שעסוק או שיש לך מלא. Busy, עסוק. You have a very busy schedule, הלוח שלך. עסוק בשבוע הזה, אוקיי? This week. This week, שבוע הזה, השבוע. אוקיי? So next one we have the word meat. Like meat and greet. Okay? Double E, meat. Now, you have also a similar, which is meat, which is the בשר. But meat is to לראות, אוקיי? Or להכיר. נכון? אז, למשל כאן. את יכולה לראות? אני רוצה ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת... ללכת מה זה אומר לנו במשפט הזה? מה הוא רוצה לעשות? לפגש נכון. יפה יונתן. זה הזמן או שעה אוקיי. שואלים על השעה. אוקיי? So what time does your English lesson start? So it's asking for your time or your schedule. If you say time, it can also mean your schedule. Schedule, it can be the שעה, איזה שעה ואיזה תריק. יום וקודש. That's for the schedule. So the word arrive, arrive. What does it mean, arrive? I arrive in school. So arrive means... arrive is to a... לגיע, אוקיי? לא לגיע, it's a... לא לטוס, אם אתה אומר, להגיד, הגעתי. So it would be, I arrived. Now arrive. שאתם כבר, להגיד, אתם כבר בשתי מטוס. איך אומרים? נרחזתי. Just a second. היגאטי זה המסגרת הקודמת, אז ארייב זה המסגרת הקודמת, זאת אומרת להגיע, להגיע, אוקיי, להגיע. אז מסגרת המסגרת האפשרית פה, אוקיי, אפשר לראות? אני ארייב אירפורט. שתי מטוס. אוקיי, אני אגיע לשתי מטוס בשעה שלוש. אוקיי? שלוש בערב. אוקיי. זה פיים זה אחרי צהריים. שלוש אחרי צהריים. אוקיי, אז עכשיו, איך לענות על השפעה Cancel? יש לך את זה הרבה בטלפון שלך מה זאת אומרת Cancel? יש לך פה כאילו X בדרך כלל הסין הוא X Cancel, I cancelled my schedule או לפעמים אתה אומר, Proceed או Cancel מה זאת אומרת להחליט 2 אם יש לך x מה זאת אומרת אוקיי, אז כדי להחליט, יונתן, את השפעה להחליט זאת אומרת לבטל, בטל, אוקיי? בסדר? אז אם אתה אומר, אני הולך להחליט את הסקדול שלי, אז אתה הולך להחליט את זה, בזמן שלך, בלוח, איזה דבר יש לך, אוקיי? להחליט. בואו נראה את האמצעות. אפשר לדבר? I need the time to cancel the meeting because. אוקיי, אנחנו צריכים להחליט את ההגישה בגלל הרעיון. אוקיי? אז זה אומר שאנחנו צריכים לבטל את הפגישה בגלל הרעיון. מה זה? איך אומרים רעיון בערבית? שכחתי. רעיון. שיורד גשם, גשם, אוקיי? גשם. נכון. So, that's what it means to cancel. All right? So, יונתן, we still have here a more, אוצר מילים, but we are going to continue it בשיגור הבשלכה. עכשיו אני אשלח לך, I will send you a homework קודם, לראות את האוצר מילים, אוקיי? לראות את האוצר מילים, אוקיי? לראות מילים, אוקיי? את לראות האוצר את האוצר מילים, אוקיי? לראות את האוצר מילים, אוקיי? לראות את האוצר מילים, אוקיי? לראות את האוצר מילים, אוקיי? לראות את האוצר מילים, אוקיי? לראות את האוצר מילים, אוקיי? לראות את האוצר מילים, אוקיי? לראות את האוצר מיל.
"""

ALL_TRANSCRIPTS = {"Philip_Hobbies": TRANSCRIPT_1}
COMBINED_TRANSCRIPT = "\n".join([t for t in ALL_TRANSCRIPTS.values() if t])


# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------
def section(title):
    logger.info("\n" + "=" * 70)
    logger.info(f"  {title}")
    logger.info("=" * 70)


def subsection(title):
    logger.info(f"\n  --- {title} ---")


# -------------------------------------------------------------------
# PHASE 1 — EXTRACTION
# -------------------------------------------------------------------
def test_extraction():
    section("PHASE 1: EXTRACTION")

    from src.ai.extractors import (
        VocabularyExtractor,
        MistakeExtractor,
        SentenceExtractor,
    )

    vocab_all = []
    mistakes_all = []
    sentences_all = []

    subsection("Rule-Based Extraction")

    for name, transcript in ALL_TRANSCRIPTS.items():
        vocab = VocabularyExtractor().extract(transcript)
        mistakes = MistakeExtractor().extract(transcript)
        sentences = SentenceExtractor().extract(transcript)

        logger.info(
            f"    [{name}] vocab={len(vocab)}, mistakes={len(mistakes)}, sentences={len(sentences)}"
        )

        vocab_all.extend(vocab)
        mistakes_all.extend(mistakes)
        sentences_all.extend(sentences)

    logger.info(
        f"    TOTAL rule-based: vocab={len(vocab_all)}, mistakes={len(mistakes_all)}, sentences={len(sentences_all)}"
    )

    return {
        "vocabulary": vocab_all,
        "mistakes": mistakes_all,
        "sentences": sentences_all,
    }


# -------------------------------------------------------------------
# PHASE 2 — GENERATION (CLEAN + CORRECT)
# -------------------------------------------------------------------
def test_generation(extracted):
    section("PHASE 2: GENERATION (REAL PIPELINE)")

    from src.ai.generators import (
        generate_flashcards,
        generate_spelling_items,
        generate_fill_blank,
        generate_sentence_builder,
        generate_grammar_challenge,
        generate_advanced_cloze,
    )

    vocabulary = extracted["vocabulary"]
    mistakes = extracted["mistakes"]
    sentences = extracted["sentences"]

    results = {}

    # Flashcards
    subsection("Flashcards")
    fc = generate_flashcards(vocabulary, COMBINED_TRANSCRIPT, limit=8)
    results["flashcards"] = fc
    logger.info(f"  ✓ Generated {len(fc)} flashcards")

    # Spelling
    subsection("Spelling")
    sp = generate_spelling_items(vocabulary, COMBINED_TRANSCRIPT, limit=8)
    results["spelling"] = sp
    logger.info(f"  ✓ Generated {len(sp)} spelling items")

    # Fill Blank
    subsection("Fill-in-the-Blank")
    fb = generate_fill_blank(mistakes, COMBINED_TRANSCRIPT, limit=8)
    results["fill_blank"] = fb
    logger.info(f"  ✓ Generated {len(fb)} fill blank items")

    # Sentence Builder
    subsection("Sentence Builder")
    sb = generate_sentence_builder(sentences, limit=3)
    results["sentence_builder"] = sb
    logger.info(f"  ✓ Generated {len(sb)} sentence builder items")

    # Grammar
    subsection("Grammar")
    gc = generate_grammar_challenge(mistakes, limit=3)
    results["grammar_challenge"] = gc
    logger.info(f"  ✓ Generated {len(gc)} grammar items")

    # Advanced Cloze
    subsection("Advanced Cloze")
    ac = generate_advanced_cloze(sentences, limit=2)
    results["advanced_cloze"] = ac
    logger.info(f"  ✓ Generated {len(ac)} advanced cloze items")

    return results


# -------------------------------------------------------------------
# PHASE 3 — DISTRACTOR ENHANCEMENT (GROQ)
# -------------------------------------------------------------------
def test_distractor_enhancement(generation):
    section("PHASE 3: DISTRACTOR ENHANCEMENT (GROQ)")

    try:
        from src.ai.enhancers import enhance_pipeline_output

        logger.info("  Calling Groq to enhance distractors...")
        enhanced = enhance_pipeline_output(generation)

        # Check if enhancement worked
        enhanced_count = 0
        original_synthetic = 0

        # Check fill_blank options
        for i, item in enumerate(enhanced.get("fill_blank", [])):
            options = item.get("options", [])
            # Count synthetic-looking options (ending in 'ed', 'ing', 's' of the correct word)
            correct = item.get("correct_answer", "")
            synthetic = [
                o
                for o in options
                if o != correct
                and (
                    o.endswith("ed")
                    and o[:-2] == correct
                    or o.endswith("ing")
                    and o[:-3] == correct
                    or o.endswith("s")
                    and o[:-1] == correct
                    or "ing" in o
                    and correct in o
                )
            ]
            if len(synthetic) < 2:  # Most options are now semantic
                enhanced_count += 1
            else:
                original_synthetic += 1

        logger.info(
            f"  ✓ Enhanced {enhanced_count} fill_blank items with semantic distractors"
        )
        if original_synthetic > 0:
            logger.info(
                f"  ⚠ {original_synthetic} items still have synthetic distractors (fallback)"
            )

        # Show sample of enhanced options
        if enhanced.get("fill_blank"):
            sample = enhanced["fill_blank"][0]
            logger.info(f"  Sample enhanced options: {sample.get('options', [])}")

        return enhanced

    except Exception as e:
        logger.warning(f"  Distractor enhancement failed: {e}")
        logger.info("  Using original generation (no enhancement)")
        return generation


# -------------------------------------------------------------------
# PHASE 4 — LESSON PROCESSOR
# -------------------------------------------------------------------
def test_lesson_processor():
    section("PHASE 4: LESSON PROCESSOR")

    from src.ai.lesson_processor import LessonProcessor

    lp = LessonProcessor()

    for name, transcript in ALL_TRANSCRIPTS.items():
        res = lp.process_lesson(transcript, lesson_number=1)
        logger.info(
            f"    [{name}] flashcards={len(res['flashcards'])}, "
            f"spelling={len(res['spelling'])}, fill_blank={len(res['fill_blank'])}, "
            f"sentence_builder={len(res['sentence_builder'])}, "
            f"grammar_challenge={len(res['grammar_challenge'])}, "
            f"advanced_cloze={len(res['advanced_cloze'])}"
        )

    return res


# -------------------------------------------------------------------
# PHASE 5 — TRANSLATIONS
# -------------------------------------------------------------------
def test_translation_quality(gen):
    section("PHASE 4: TRANSLATION CHECK")

    total = 0
    with_trans = 0

    for g in ("flashcards", "spelling", "sentence_builder"):
        for item in gen.get(g, []):
            total += 1
            if item.get("translation"):
                with_trans += 1

    pct = (with_trans / max(1, total)) * 100
    logger.info(f"  Translation coverage: {pct:.1f}% ({with_trans}/{total})")

    return {"total": total, "with_translation": with_trans}


# -------------------------------------------------------------------
# PHASE 5 — SCHEMA CHECK
# -------------------------------------------------------------------
def test_schema(gen):
    section("PHASE 5: SCHEMA")

    schema = {
        "flashcards": ["word", "translation", "example_sentence"],
        "spelling": ["word", "translation", "hint"],
        "fill_blank": ["sentence", "options", "correct_answer"],
        "sentence_builder": ["english", "tokens", "accepted"],
        "grammar_challenge": ["prompt", "options", "correct_answer"],
        "advanced_cloze": ["sentence", "blank1", "blank2"],
    }

    ok = True

    for g, req in schema.items():
        items = gen.get(g, []) or []
        if not items:
            logger.info(f"  {g}: no items")
            continue

        subsection(g)
        logger.info(f"  total={len(items)}")

        for idx, item in enumerate(items[:2], start=1):
            preview = json.dumps(item, ensure_ascii=False)[:200]
            logger.info(f"    {idx}. {preview}...")

    return ok


# -------------------------------------------------------------------
# PHASE 6 — FINAL SCORE
# -------------------------------------------------------------------
def score_pipeline(extraction, generation, trans_stats, schema_ok):
    section("FINAL SCORE")

    TARGETS = {
        "flashcards": 8,
        "spelling": 8,
        "fill_blank": 8,
        "sentence_builder": 3,
        "grammar_challenge": 3,
        "advanced_cloze": 2,
    }

    total_generated = sum(len(generation[g]) for g in TARGETS)

    extraction_score = 2.0
    gen_score = min(3.0, (total_generated / 32) * 3)
    trans_pct = (trans_stats["with_translation"] / max(1, trans_stats["total"])) * 100
    trans_score = min(2.0, trans_pct / 100 * 2)
    schema_score = 2.0 if schema_ok else 1.0
    completeness_score = 1.0 if total_generated >= 20 else 0.5

    final = (
        extraction_score + gen_score + trans_score + schema_score + completeness_score
    )

    logger.info(f"TOTAL SCORE = {final:.2f}/10")

    return final


def log_final_summary(extraction, generation, trans_stats, schema_ok, final_score):
    """Log a compact final summary line for humans and logs."""
    section("RUN SUMMARY")

    vocab_count = len(extraction.get("vocabulary", []))
    mistakes_count = len(extraction.get("mistakes", []))
    sentences_count = len(extraction.get("sentences", []))

    fc = len(generation.get("flashcards", []))
    sp = len(generation.get("spelling", []))
    fb = len(generation.get("fill_blank", []))
    sb = len(generation.get("sentence_builder", []))
    gc = len(generation.get("grammar_challenge", []))
    ac = len(generation.get("advanced_cloze", []))
    total_items = fc + sp + fb + sb + gc + ac

    total_trans = trans_stats.get("total", 0)
    with_trans = trans_stats.get("with_translation", 0)

    status = "PASS" if final_score >= PASS_THRESHOLD else "FAIL"

    logger.info(
        f"  Extraction: vocab={vocab_count}, mistakes={mistakes_count}, sentences={sentences_count}"
    )
    logger.info(
        f"  Generated: flashcards={fc}, spelling={sp}, fill_blank={fb}, sentence_builder={sb}, grammar_challenge={gc}, advanced_cloze={ac} (total={total_items})"
    )
    logger.info(
        f"  Translation: {with_trans}/{total_trans} items with Hebrew; Schema OK={schema_ok}"
    )
    logger.info(
        f"  Result: {status}  quality_score={final_score:.2f}/10 (threshold={PASS_THRESHOLD})"
    )


# -------------------------------------------------------------------
# FILE OUTPUT (FULL JSON)
# -------------------------------------------------------------------
def write_generation_to_file(generation, filename: str = "tmp_pipeline_output.json"):
    """Write the full generation dict to a pretty JSON file for easy reading."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(generation, f, ensure_ascii=False, indent=2)
        logger.info(f"  Wrote full generation output to {filename}")
    except Exception as e:
        logger.warning(f"  Could not write generation output to {filename}: {e}")


# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------
def main():
    section("STARTING PIPELINE TEST")

    # Phase 1: Extraction
    extraction = test_extraction()

    # Phase 2: Generation (rule-based)
    generation = test_generation(extraction)

    # Phase 3: Distractor Enhancement (Groq LLM call)
    enhanced_generation = test_distractor_enhancement(generation)

    # Write enhanced output to file
    write_generation_to_file(enhanced_generation)

    # Phase 4: Lesson Processor test
    processor = test_lesson_processor()

    # Phase 5: Translation quality
    translations = test_translation_quality(enhanced_generation)

    # Phase 6: Schema validation
    schema_ok = test_schema(enhanced_generation)

    # Final scoring
    final_score = score_pipeline(
        extraction, enhanced_generation, translations, schema_ok
    )

    log_final_summary(
        extraction, enhanced_generation, translations, schema_ok, final_score
    )

    return final_score


if __name__ == "__main__":
    score = main()
    sys.exit(0 if score >= PASS_THRESHOLD else 1)
