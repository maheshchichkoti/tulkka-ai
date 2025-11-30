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
basmala emam: Hello? basmala emam: Hello? Khadija: Hi. basmala emam: Hi! Khadija: Mahaba. basmala emam: How would you… Khadija: Bye. basmala emam: Okay, can you open the camera, please? Khadija: Okay. basmala emam: Thank you. basmala emam: Hi, how are you? Khadija: Bye. basmala emam: Your name is Khadija, right? Khadija: Yes. basmala emam: Okay, my name is Pass now, okay? Khadija: Okay. basmala emam: Okay, so how are you? Khadija: Good, fine. basmala emam: Okay, it's great. How old are you? Khadija: enforcement. basmala emam: 14, oh, it's amazing! basmala emam: Okay, I think you already know the letters, right? Khadija: Yes. basmala emam: Yes, okay. basmala emam: So let's start. Khadija: Are you ready? Okay. basmala emam: What did you do in the morning? Khadija: I, eat breakfast. basmala emam: Before that. Khadija: Before I wake up. basmala emam: Yeah, good job. Khadija: And I brush my face. basmala emam: Good job! Khadija: Evan, where are you? Khadija: It's breakfast. basmala emam: Yeah, okay. So you, want to know more about mourning? Khadija: Yes. basmala emam: Okay, let's go. basmala emam: So now… or do you see the screen? Khadija: Yes. basmala emam: Okay. basmala emam: So now, we were talking about… Morning. basmala emam: Okay… Are you ready? So, at number one, the book is Good Morning. basmala emam: Okay, the name of the book? basmala emam: So, in the morning, we say good morning, right? Khadija: Correct. basmala emam: Okay, let's go to the next. basmala emam: So, number one, the kitchen number one, it's morning, right? Khadija: Yes. basmala emam: morning, okay? And next, we wake up, as you see, Yes. Wake up. basmala emam: Right, and then wash face… Right? basmala emam: And brushed teeth. basmala emam: Okay, you already know that, excellent. basmala emam: Okay, so she say good morning. She say good morning. basmala emam: Then, you wake up… Okay… And then? basmala emam: I wash my face, because this is my face, when I want to talk about basmala emam: saying is mine, and hagyptati, I say my. basmala emam: Right? basmala emam: I wash my face. Excellent. basmala emam: Okay, I… then I brush my teas. basmala emam: I brush my teeth. Khadija: Yeah. basmala emam: Good job! basmala emam: Next. basmala emam: Can you complete? Khadija: Good morning. basmala emam: Amazing. Khadija: Wake up. basmala emam: Yeah, good job. You know the spelling, right? Khadija: Yes. basmala emam: Okay. I… Khadija: I, wash my face, my, face. basmala emam: Yeah, excellent. Khadija: And, this, I wash my teeth. basmala emam: Not wash, brush. Khadija: Brush. basmala emam: My teeth. Khadija: Mighty, okay. basmala emam: Okay, Prash, P-R-U-S-H. Okay. Khadija: Brush my… basmala emam: Yeah, and Walsh, it's W-A-S-H, okay? basmala emam: Okay, let's go to the next. basmala emam: Okay… Khadija: Okay. basmala emam: Okay, now… Dress up, Yanni. basmala emam: What? Khadija: No, no, nothing. basmala emam: Okay, dress up, Yanni. Khadija: Urzo, Piane enlas. basmala emam: Yeah, good job. Dress up! Khadija: Dressed? basmala emam: up. Yeah, then break fast. Khadija: Yeah. basmala emam: Break first, okay? And then you go to school, right? Khadija: Yes. basmala emam: And work? Who is good to work? Khadija: And… The father… basmala emam: Yeah. basmala emam: Good job! basmala emam: Good job. Okay, so you go to school, and your dad go to work, right? Khadija: Yes. basmala emam: Okay, then, when I want to talk about myself, I say I, I dress up, Okay… basmala emam: And next, I eat breakfast. basmala emam: Yeah, where is the verb? Khadija: They eat. basmala emam: Yeah, and subject? Khadija: Breakfast. basmala emam: No, subject, el feal. Subject. Khadija: Oi. basmala emam: Yeah, do you know the subjects? Khadija: Yes, unfair. En faire. basmala emam: Yeah, good job. basmala emam: Okay, next. I… Khadija: Go to school. basmala emam: Yeah, amazing. So where is the verb? Khadija: Go. basmala emam: Amazing! basmala emam: And the subject is I, right? Khadija: Yes. basmala emam: Okay, next. basmala emam: I go to work. basmala emam: Right? Khadija: Well, the verb… basmala emam: The… Khadija: the microphone. basmala emam: Father, my father, go to work. basmala emam: Yeah. Khadija: Woof. basmala emam: Good job. Okay, now I… Khadija: Idress of… basmala emam: Amazing. Khadija: I eat breakfast. basmala emam: Good job. Khadija: I go to school… basmala emam: Okay? Yeah. Khadija: A work. basmala emam: Okay. basmala emam: So now, what we eat at the breakfast, and I'm making a forbidden photo. basmala emam: Okay? What do you eat in the breakfast? What do you eat? Khadija: Like sandwich and eggs. basmala emam: Yeah, amazing. Okay. Any… something else? Khadija: Salad? basmala emam: Yeah? Khadija: Yes. basmala emam: Okay, so, number one is sandwich. basmala emam: Sandwich. basmala emam: And Syria? Do you know Syria? Khadija: Yes. basmala emam: Okay, do you know what is this? basmala emam: Like, corn flicks. Khadija: Yes, look, please. basmala emam: Yeah, okay, and what else? Khadija: Egg. basmala emam: Yeah, good job, and… Khadija: Rise. basmala emam: And? basmala emam: And… Fruits, good job. basmala emam: Okay, now, one… the first one is… Khadija: Roads. Khadija: Rise. Khadija: Sandwich. basmala emam: Yeah? Khadija: Salad. basmala emam: Yeah? Khadija: Eggs? basmala emam: The last one? Khadija: I just know. basmala emam: Syria. Khadija: To remember. basmala emam: Serial. Khadija: Yes, seriously. basmala emam: Yeah, good job. basmala emam: I think it's too easy for you, so easy, right? Khadija: Okay. basmala emam: You can draw a line. Khadija: Eggs do… basmala emam: Yeah, you can't… you can't rule, there is a pin in the bottom of screen. Khadija: Oh, yeah. basmala emam: P… Khadija: Yeah, good job. basmala emam: Fruit, salad, yeah, amazing. basmala emam: Okay… One minute. basmala emam: Zen? basmala emam: You know, number one is… Khadija: And… right? Khadija: Nope. basmala emam: Yeah? basmala emam: Yeah, can you… Tell me what the first one is? Khadija: Rise. basmala emam: Y-yeah? Khadija: Sandwich. basmala emam: And? Khadija: Zero. basmala emam: Syria. Khadija: Yes. basmala emam: Okay, good job! basmala emam: You are very, very, very excellent. Khadija: Let's go to another lesson. basmala emam: Okay… Now, let's start with… Afternoon, okay? What are you doing in the afternoon? Khadija: And… basmala emam: Yeah. Khadija: Emm… I eat… basmala emam: Meh. basmala emam: Twat. In the morning, we eat breakfast. Khadija: In afternoon, we eat. basmala emam: Yes. What we eat what? Yeah. basmala emam: In the morning, we eat breakfast. In the morning. So, in the afternoon, what we eat basmala emam: Oh, you understand? Khadija: Unra de. basmala emam: Yeah, launch. Khadija: Lunch. basmala emam: Yeah, good job. Khadija: lunch, and… I dress up… basmala emam: Good job. basmala emam: Study. Khadija: Yes, study it, and both scanned. basmala emam: Okay, so now let's learn the new words. In afternoon. Are you ready? Khadija: Yes. basmala emam: Let's go. basmala emam: Okay, so this is a song about how grating. basmala emam: Do you know how grading? basmala emam: Oh, hello, how are you? basmala emam: Good, great, wonderful. Do you want to listen to this song? Khadija: Maybe, yes. basmala emam: Okay, let's listen to Giz. Khadija: I don't listen. basmala emam: You don't listen? Khadija: No, there are no seas… basmala emam: Sound, okay, one minute. Khadija: Yes. basmala emam: My sync now… Audio shared by basmala emam: Hello? Audio shared by basmala emam: Hello, hello, how are you? Hello? Hello? Hello, how are you? I'm good! Audio shared by basmala emam: I'm great! Audio shared by basmala emam: I'm wonderful, I'm good! Audio shared by basmala emam: I'm great I'm wonderful Hello? Audio shared by basmala emam: Hello, hello, how are you? Hello, hello, hello, how are you? I'm tired. Audio shared by basmala emam: I'm hungry! Audio shared by basmala emam: I'm not so good, I'm tired. Audio shared by basmala emam: I'm hungry! Audio shared by basmala emam: I'm not so good. Audio shared by basmala emam: Hello? Audio shared by basmala emam: Hello, hello, how are you? Hello, hello, hello, how are you? Audio shared by basmala emam: How are you? basmala emam: Okay. basmala emam: So now… How are you grading each other? basmala emam: Hello? How are you? Right? Khadija: Right. basmala emam: If you're good… Great. basmala emam: Wonderful. Khadija: Yes. basmala emam: Yeah, if you nut… How you… can you see? Khadija: Yes, yes. basmala emam: I'm tired, I'm hungry, I'm not too good, okay? If you're not good. basmala emam: You already knew that, right? Khadija: Yes. basmala emam: Okay, let's go to next. basmala emam: So… Let's go… So, in the afternoon, Afternoon, Reed. basmala emam: Okay. Watch TV. basmala emam: Or play, right? Do you love reading? Khadija: And… not too much. basmala emam: Okay, so you love podcasts? Khadija: What is BTSCAD? basmala emam: podcast is not to read. You listen to a box. Someone read it to you. basmala emam: You love that, right? Khadija: Yes. Can you tell me which podcast you listen? basmala emam: Mmm. Khadija: I don't remember what name I'll book. basmala emam: If you, if you love broadcasts, I can recommend podcasts for you. basmala emam: to improve your English. Khadija: Yes, I love that, but I don't remember what is a book I, a sound. basmala emam: Yeah, I… I can recommend. basmala emam: Okay, if you want. Khadija: Fa. basmala emam: Okay, one minute. basmala emam: You have an application podcast? basmala emam: It's the app? Khadija: No. basmala emam: Okay, no problem, you can listen from it in YouTube. basmala emam: If you want. basmala emam: There is a channel called Easy English. basmala emam: Okay, you can listen to these videos, And you will read… Khadija: What the name? basmala emam: Easy English. basmala emam: And what else? One minute. basmala emam: I love this channel so much. One minute. basmala emam: What? You say something? Khadija: No, no. basmala emam: Okay… Khadija: Is it English? What? basmala emam: Yeah, easy English. Khadija: Okay. basmala emam: Okay, and the next time, I will, collecting the channels and, tell you, okay? basmala emam: Hagamal channels? basmala emam: English, okay? Khadija: You are speaking to Wood. basmala emam: Speaking so good. Khadija: A, oof. basmala emam: Okay. Okay. basmala emam: So, in afternoon, we read. basmala emam: Write, read, watch TV, and play. basmala emam: Okay… Khadija: it. Khadija: So, next… basmala emam: Good afternoon! Like, good morning. Good afternoon, okay. basmala emam: Next, I read a book. basmala emam: Ay? Khadija: a book. basmala emam: Read a book. Khadija: Yes. basmala emam: Oh, you read a book. Yeah. Khadija: Yep. basmala emam: Can you repeat? Khadija: I read a book. basmala emam: Yeah, good job where is the verb. Khadija: Read. basmala emam: Yeah, good job. And subject… Khadija: Bye. basmala emam: Yeah, amazing. Okay, I watch TV. Khadija: I watch TV. basmala emam: Yeah, or we watch TV. We watch TV. basmala emam: Right? basmala emam: You lose the subject, right? All subjects. All of them. basmala emam: I… Khadija: Aye. basmala emam: Hit the AND… Khadija: And, we are the… basmala emam: We are they, and what else? Khadija: And… Khadija: Is, he or she like this? basmala emam: Yeah, he, she, and? Last one? basmala emam: Et, yeah, good job, amazing! basmala emam: Okay, and I… Khadija: Play a game. basmala emam: Good job. Where is the verb? Khadija: play. basmala emam: Yeah? basmala emam: So good. Khadija: Good afternoon. basmala emam: Yeah, I… Khadija: You read a book. basmala emam: Amazing. basmala emam: Ay? Khadija: I watch TV. basmala emam: And I… Khadija: I play a game. basmala emam: Yeah, good job. basmala emam: Okay, and what else we do in the afternoon? We study, yeah. Khadija: And clean, and go home. basmala emam: Yeah, back from school? basmala emam: And go home. Yeah, good job. So, I study English, like now. We study English, right? Khadija: Right. basmala emam: So I study English. Khadija: I study English. basmala emam: Yeah, and? Khadija: I eat lunch. basmala emam: Good job. basmala emam: I… Khadija: I glean thou helps. basmala emam: Yeah, amazing. basmala emam: Aye? Khadija: I go home. basmala emam: Yeah, amazing. basmala emam: Aye? Khadija: I, study English. basmala emam: Amazing. Khadija: I eat lunch. basmala emam: Launch. Khadija: Not much. basmala emam: Yeah? Khadija: I cleaned the house. basmala emam: Amazing. Khadija: You go… Like, what? basmala emam: See? Khadija: Yes. basmala emam: Yeah, good job. basmala emam: Okay, what we eat at lunch? basmala emam: Okay… Khadija: Maybe chicken? basmala emam: Yeah? Khadija: Models… basmala emam: Yeah, what's your favorite? Khadija: My favorite, chicken, maybe, or meat. basmala emam: Neat. basmala emam: Maybe something, not here? basmala emam: Hagam Shmongu tehena. Khadija: Christian, yeah. Hi, Philip. basmala emam: beads. Khadija: And… basmala emam: sushi. Khadija: Chicken. Oh, of pumpkin sushi. basmala emam: Yeah! basmala emam: Me too. Okay. basmala emam: So, number one is fish, it's easy. Chicken. Khadija: No, it does? Khadija: Just to bulls? basmala emam: Good job! Khadija: Mate. basmala emam: Yeah, amazing. basmala emam: Okay, so now, number one… Khadija: meet. Mr. Bills. Khadija: Fish. Khadija: So… Noodles and chicken. basmala emam: Good job! basmala emam: You are perfect, ready, okay. Khadija: Thank you. basmala emam: Welcome! Khadija: Damn. basmala emam: So, this is what… basmala emam: Yeah. basmala emam: Okay, you make it try it. basmala emam: Okay. basmala emam: And next… basmala emam: Yeah, amazing. basmala emam: Okay… So, we end the next lesson, too. Okay. Do you remember what we take today? Khadija: Good morning, and good afternoon. basmala emam: Yeah, do you remember what we do in the morning? Khadija: Yeah, we wake up and, wash… Khadija: My face, and wash… no, no. And, brush my teeth. basmala emam: Yeah, amazing. Khadija: And eat breakfast. basmala emam: And… Dress? basmala emam: dress up. Yeah? Khadija: Do esa… What is dursing? basmala emam: Dressing up? Khadija: Yes. basmala emam: Good job. It's present continuous, right? Khadija: Yes. And… go to school. basmala emam: Yeah… And your dad? Khadija: My dad got to work. basmala emam: Yeah, amazing. Khadija: Afternoon, we… basmala emam: We eat and the breakfast first. Khadija: Like, egg, and salad. basmala emam: Yeah? Khadija: Fruits. Sandwich. Fruits… basmala emam: Yeah, amazing. Khadija: Yes. basmala emam: Seriously. basmala emam: Okay. Khadija: Okay, and afternoon, we, we go to home, and… we… And clean the house. basmala emam: Mmm… Khadija: Let me get flaring… basmala emam: Eat lunch! Khadija: It's lunch, yes, and… basmala emam: book. Khadija: Maybe. basmala emam: Read a book. Khadija: Yes, do you read a book? basmala emam: book, study English, or something else. basmala emam: Yeah. basmala emam: What else? Play a game? Khadija: It's blank. basmala emam: Okay, you are amazing. Ready? You are amazing today. So, I will ask you something. I think you know the colors and numbers, fruits and vegetables. Khadija: Right? Khadija: Yes, but no, the O. basmala emam: What? Khadija: No, the A, the L. Khadija: Ishkulhan. basmala emam: Mshkun lil e. basmala emam: Yeah. basmala emam: Okay. basmala emam: So, we can continue in this book. basmala emam: What do you think? What's your opinion? Khadija: ist. basmala emam: Good morning, good afternoon. Good evening. basmala emam: Okay… Khadija: hello? Khadija: Yeah. basmala emam: kete. basmala emam: With a Saharadiki? Khadija: Hi, I did. basmala emam: My class, toys, family, house… Khadija: And… I have a debut far, it should be… basmala emam: Colors and numbers, fruits and vegetables, days of the week. Khadija: Great. Khadija: Maybe. Days of. basmala emam: Zoek. Khadija: Yes. basmala emam: Okay, and farm animals, shapes… Khadija: Yeah, maybe. Khadija: Okay? basmala emam: Habi Oktar. Khadija: Yup. basmala emam: Okay, Nikkammer Kebeh? Khadija: Boom. basmala emam: Okay, so I will send you your homework. basmala emam: Okay, it's so easy. Okay, it's, review. Review about we talk today. basmala emam: Okay… So, thank you so much for your time. basmala emam: Okay. basmala emam: You're welcome. See you next class. Bye-bye! Khadija: Bye-bye!
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

    from src.ai.extractors import VocabularyExtractor, MistakeExtractor, SentenceExtractor

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
# PHASE 3 — LESSON PROCESSOR
# -------------------------------------------------------------------
def test_lesson_processor():
    section("PHASE 3: LESSON PROCESSOR")

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
# PHASE 4 — TRANSLATIONS
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

    final = extraction_score + gen_score + trans_score + schema_score + completeness_score

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

    extraction = test_extraction()
    generation = test_generation(extraction)
    write_generation_to_file(generation)
    processor = test_lesson_processor()

    translations = test_translation_quality(generation)
    schema_ok = test_schema(generation)
    final_score = score_pipeline(extraction, generation, translations, schema_ok)

    log_final_summary(extraction, generation, translations, schema_ok, final_score)

    return final_score


if __name__ == "__main__":
    score = main()
    sys.exit(0 if score >= PASS_THRESHOLD else 1)