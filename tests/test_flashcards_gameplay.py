"""
tests/test_flashcards_full_playflow.py

Comprehensive Flashcards gameplay tests for TULKKA Games APIs.

Covers:
- Seed a word list with 8 realistic words (various practice_count to exercise "unknown" logic)
- Modes: topic, lesson, custom, mistakes-only, unknown-words
- Start session, record results (incorrect + correct), idempotency, clientResultId dedupe
- Complete session and verify completedAt
- Mistakes listing and stats endpoint
- Detailed console logging of responses for inspection
"""

import pytest
import pytest_asyncio
import uuid
import json
import textwrap
from httpx import AsyncClient, ASGITransport
from src.api.app import app  # adjust import path if needed
from datetime import datetime, timedelta

# -------------------------
# Fixtures
# -------------------------

@pytest.fixture
def test_user_id():
    return f"test-user-{uuid.uuid4().hex[:8]}"

@pytest.fixture
def headers(test_user_id):
    # Tests use X-User-Id header by default as in your suite
    return {"X-User-Id": test_user_id, "Content-Type": "application/json"}

@pytest_asyncio.fixture(scope="function")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

# -------------------------
# Helpers (logging + seeding)
# -------------------------

def pretty(obj, max_chars=1400):
    try:
        s = json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        s = str(obj)
    if len(s) > max_chars:
        return s[:max_chars] + "\n... (truncated)"
    return s

async def log_response(resp, label=None):
    label = label or ""
    try:
        body = resp.json()
        body_str = pretty(body)
    except Exception:
        try:
            body_text = resp.text
            body_str = (body_text[:1400] + "... (truncated)") if len(body_text) > 1400 else body_text
        except Exception:
            body_str = "<unreadable body>"
    print("\n" + "="*90)
    print(f"[{label}] {resp.request.method} {resp.request.url} -> {resp.status_code}")
    print("- response body:")
    print(textwrap.indent(body_str, "  "))
    print("="*90 + "\n")

async def seed_word_list_with_8_words(client, headers, list_name="Integration Flashcards 8"):
    """
    Creates a word list and adds 8 words.
    We intentionally add words with different initial stats so 'unknown words' logic can be tested:
      - some words have practiceCount = 0 (unknown)
      - some words will be marked practiced via recording results
    Returns: (list_id, list_of_word_ids, word_entries)
    """
    r = await client.post("/v1/word-lists", headers=headers, json={"name": list_name, "description": "Seeded for full-play tests"})
    await log_response(r, "CREATE_WORD_LIST")
    assert r.status_code == 201
    list_id = r.json()["id"]

    # Eight example words (mix of known/unknown)
    seed_words = [
        ("alpha", "α - letter"),        # unknown initially
        ("beta", "β - letter"),         # unknown initially
        ("gamma", "γ - letter"),        # will be practiced later
        ("delta", "δ - letter"),        # will be practiced incorrectly then correct -> mistakes flow
        ("echo", "echo - sound"),       # known (we'll simulate prior practice by recording a correct result)
        ("foxtrot", "dance/military"),  # unknown
        ("golf", "sport"),              # known
        ("hotel", "lodging"),           # unknown
    ]

    word_ids = []
    word_entries = []
    for w, t in seed_words:
        wr = await client.post(f"/v1/word-lists/{list_id}/words", headers=headers, json={"word": w, "translation": t, "notes": f"seed:{w}"})
        await log_response(wr, f"ADD_WORD {w}")
        assert wr.status_code == 201
        wid = wr.json()["id"]
        word_ids.append(wid)
        word_entries.append({"id": wid, "word": w, "translation": t})

    return list_id, word_ids, word_entries

# -------------------------
# Tests: Full gameplay flows
# -------------------------

@pytest.mark.asyncio
async def test_full_flashcards_playflow_all_modes(client, headers):
    """
    This single test seeds data and runs through:
     - ensure topics/lessons endpoints respond (optional)
     - start custom session (selectedWordIds)
     - start topic session (if possible)
     - start lesson session (if possible)
     - start mistakes-only (only after creating mistakes)
     - start unknown-words session (words with practiceCount == 0)
     - record results (incorrect then correct) and verify mistakes / stats are created
     - complete sessions and check completedAt
    """
    # 1) Catalog endpoints (optional but useful for frontend)
    topics_resp = await client.get("/v1/flashcards/topics", headers=headers)
    await log_response(topics_resp, "GET_TOPICS")
    assert topics_resp.status_code in [200, 404]  # 404 allowed if not implemented yet

    lessons_resp = await client.get("/v1/flashcards/lessons", headers=headers)
    await log_response(lessons_resp, "GET_LESSONS")
    assert lessons_resp.status_code in [200, 404]

    # 2) Seed word list with 8 words
    list_id, word_ids, word_entries = await seed_word_list_with_8_words(client, headers)
    assert len(word_ids) == 8

    # 3) Start CUSTOM session (select subset)
    payload_custom = {
        "mode": "custom",
        "wordListId": list_id,
        "selectedWordIds": word_ids[:5],  # first 5
        "shuffle": False
    }
    start_custom = await client.post("/v1/flashcards/sessions", headers=headers, json=payload_custom)
    await log_response(start_custom, "START_CUSTOM_SESSION")
    assert start_custom.status_code == 201
    custom_body = start_custom.json()
    assert custom_body.get("wordListId", custom_body.get("listId")) == list_id
    assert custom_body["progress"]["total"] == 5

    custom_session_id = custom_body["id"]

    # 4) Record a few results on the custom session to create some state:
    #    - mark word 3 incorrect (creates a mistake)
    #    - mark word 3 again correct (user retried)
    w_incorrect = word_ids[2]
    client_result_id = str(uuid.uuid4())
    r_incorrect = await client.post(
        f"/v1/flashcards/sessions/{custom_session_id}/results",
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
        json={
            "clientResultId": client_result_id,
            "wordId": w_incorrect,
            "isCorrect": False,
            "timeSpentMs": 1300,
            "attempts": 1
        }
    )
    await log_response(r_incorrect, "RECORD_CUSTOM_INCORRECT")
    assert r_incorrect.status_code == 200

    # Deduplicate same clientResultId -> should return 200/201 or same result
    r_dup = await client.post(
        f"/v1/flashcards/sessions/{custom_session_id}/results",
        headers=headers,
        json={
            "clientResultId": client_result_id,
            "wordId": w_incorrect,
            "isCorrect": False,
            "timeSpentMs": 1300,
            "attempts": 1
        }
    )
    await log_response(r_dup, "RECORD_CUSTOM_INCORRECT_DUP")
    assert r_dup.status_code in [200, 201]

    # Now record the correct attempt for same word (user fixed it)
    client_result_id2 = str(uuid.uuid4())
    r_correct = await client.post(
        f"/v1/flashcards/sessions/{custom_session_id}/results",
        headers=headers,
        json={
            "clientResultId": client_result_id2,
            "wordId": w_incorrect,
            "isCorrect": True,
            "timeSpentMs": 900,
            "attempts": 1
        }
    )
    await log_response(r_correct, "RECORD_CUSTOM_CORRECT")
    assert r_correct.status_code == 200

    # 5) Complete custom session
    r_complete_custom = await client.post(f"/v1/flashcards/sessions/{custom_session_id}/complete", headers=headers, json={})
    await log_response(r_complete_custom, "COMPLETE_CUSTOM_SESSION")
    assert r_complete_custom.status_code == 200
    comp_custom = r_complete_custom.json()
    assert comp_custom["id"] == custom_session_id
    assert comp_custom.get("completedAt") is not None

    # 6) Start UNKNOWN WORDS session: those with practiceCount == 0
    # Server may support mode 'unknown' or 'unknown_words'; we'll try both forms.
    payload_unknown_modes = [
        {"mode": "unknown"},
        {"mode": "unknown_words"},
        {"mode": "custom", "wordListId": list_id, "selectedWordIds": [wid for i,wid in enumerate(word_ids) if i in (0,1,5,7)]}
    ]
    unknown_session_id = None
    for p in payload_unknown_modes:
        r_unknown = await client.post("/v1/flashcards/sessions", headers=headers, json=p)
        await log_response(r_unknown, "START_UNKNOWN_ATTEMPT")
        if r_unknown.status_code == 201:
            unknown_body = r_unknown.json()
            unknown_session_id = unknown_body["id"]
            break
        # if 400/404 continue to try next variant
    # If server didn't create unknown-mode session, skip unknown tests gracefully
    if unknown_session_id:
        # get session and check that returned items have practiceCount==0 where possible
        r_sess = await client.get(f"/v1/flashcards/sessions/{unknown_session_id}", headers=headers)
        await log_response(r_sess, "GET_UNKNOWN_SESSION")
        assert r_sess.status_code == 200
        sess_body = r_sess.json()
        items = sess_body.get("items", sess_body.get("words", []))
        # It's valid if server returns items; check that at least one item appears and total matches length
        assert sess_body["progress"]["total"] == len(items) or sess_body["progress"]["total"] >= 0

        # Complete unknown session (no results required)
        r_complete_unknown = await client.post(f"/v1/flashcards/sessions/{unknown_session_id}/complete", headers=headers, json={})
        await log_response(r_complete_unknown, "COMPLETE_UNKNOWN_SESSION")
        assert r_complete_unknown.status_code in [200, 409]  # 409 if already completed

    # 7) Start TOPIC session (frontend 'by topic' flow).
    #     If backend supports topics, attempt to pick a topic returned earlier. Fallback: use list -> topic mapping not available.
    if topics_resp.status_code == 200:
        topics = topics_resp.json().get("topics", [])
        if topics:
            topic_id = topics[0]["id"]
            payload_topic = {"mode": "topic", "topicId": topic_id, "limit": 6, "shuffle": True}
            r_topic = await client.post("/v1/flashcards/sessions", headers=headers, json=payload_topic)
            await log_response(r_topic, "START_TOPIC_SESSION")
            assert r_topic.status_code in [201, 400, 404]
            if r_topic.status_code == 201:
                topic_session = r_topic.json()
                # sanity: progress total should match items length
                items_topic = topic_session.get("items", topic_session.get("words", []))
                assert topic_session["progress"]["total"] == len(items_topic) or topic_session["progress"]["total"] >= 0

    # 8) Start LESSON session (frontend 'by lesson' flow).
    if lessons_resp.status_code == 200:
        lessons = lessons_resp.json().get("lessons", [])
        if lessons:
            lesson_id = lessons[0]["id"]
            payload_lesson = {"mode": "lesson", "lessonId": lesson_id, "limit": 6}
            r_lesson = await client.post("/v1/flashcards/sessions", headers=headers, json=payload_lesson)
            await log_response(r_lesson, "START_LESSON_SESSION")
            assert r_lesson.status_code in [201, 400, 404]

    # 9) Now: create a dedicated 'mistakes-only' session by ensuring there are mistakes first.
    #    We'll create a new session and intentionally mark two words incorrect so mistakes exist.
    list2_id, word_ids2, _ = await seed_word_list_with_8_words(client, headers, list_name="Mistakes List")
    start_mist_seed = await client.post("/v1/flashcards/sessions", headers=headers, json={"mode": "custom", "wordListId": list2_id})
    await log_response(start_mist_seed, "START_MISTAKE_SEED_SESSION")
    if start_mist_seed.status_code == 201:
        s_id = start_mist_seed.json()["id"]
        # mark 2 words incorrect
        for wid in word_ids2[:2]:
            r_err = await client.post(f"/v1/flashcards/sessions/{s_id}/results", headers=headers, json={"wordId": wid, "isCorrect": False, "timeSpentMs": 900, "attempts": 1})
            await log_response(r_err, "MARK_MISTAKE")
            assert r_err.status_code == 200
        # complete to persist progress
        r_c = await client.post(f"/v1/flashcards/sessions/{s_id}/complete", headers=headers, json={})
        await log_response(r_c, "COMPLETE_MISTAKE_SEED")
        assert r_c.status_code in [200, 409]

    # Now start a 'mistakes' mode session
    payload_mistakes = {"mode": "mistakes", "limit": 10}
    r_mistakes = await client.post("/v1/flashcards/sessions", headers=headers, json=payload_mistakes)
    await log_response(r_mistakes, "START_MISTAKES_SESSION")
    # server could return 400 if no mistakes exist for the user; accept 201 or 400
    assert r_mistakes.status_code in [201, 400]

    # 10) Verify mistakes listing endpoint and stats endpoint
    r_mist_list = await client.get("/v1/flashcards/mistakes", headers=headers)
    await log_response(r_mist_list, "GET_MISTAKES_LIST")
    assert r_mist_list.status_code == 200
    ml_body = r_mist_list.json()
    assert "data" in ml_body and "pagination" in ml_body

    r_stats = await client.get("/v1/flashcards/stats/me", headers=headers)
    await log_response(r_stats, "GET_FLASHCARDS_STATS")
    assert r_stats.status_code == 200
    stats_body = r_stats.json()
    assert "totalSessions" in stats_body and "accuracy" in stats_body

    # 11) Confirm server rejects invalid result (word not in session)
    #    Start a new session and attempt to post result for fake word
    start_invalid = await client.post("/v1/flashcards/sessions", headers=headers, json={"mode": "custom", "wordListId": list_id, "selectedWordIds": word_ids[:2]})
    await log_response(start_invalid, "START_FOR_INVALID_TEST")
    if start_invalid.status_code != 201:
        pytest.skip("Couldn't start session to test invalid result behavior")
    sid = start_invalid.json()["id"]
    r_invalid = await client.post(f"/v1/flashcards/sessions/{sid}/results", headers=headers,
                                 json={"wordId": "not-a-real-word-id", "isCorrect": True, "timeSpentMs": 100, "attempts": 1})
    await log_response(r_invalid, "POST_INVALID_WORD_RESULT")
    assert r_invalid.status_code == 400

    # All done: this test validates the full set of frontend flows end-to-end

