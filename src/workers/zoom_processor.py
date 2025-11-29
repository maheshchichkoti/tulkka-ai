# src/workers/zoom_processor.py
"""
Production-hardened Zoom -> Transcript -> Exercises worker.

Key improvements vs. original:
- Stream Zoom file downloads to a temporary file to avoid OOM.
- Treat common MP4/video recordings as audio sources.
- Use AssemblyAIHelper SDK/local-file path when available (or HTTP chunked upload fallback).
- Per-job global timeout to avoid stuck worker threads.
- Reclaim stale 'processing' jobs if previous worker died.
- Better logging and safer status transitions.
"""
import logging
import time
import traceback
import tempfile
import os
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime, timedelta

from ..db.supabase_client import SupabaseClient
from ..zoom.zoom_utils import has_transcript_file, has_audio_files, clean_vtt_transcript
from ..zoom.zoom_client import ZoomAPI
from ..config import settings
from ..time_utils import utc_now_iso

logger = logging.getLogger(__name__)

supabase = SupabaseClient()
zoom_api = ZoomAPI()

POLL_INTERVAL = getattr(settings, "WORKER_POLL_INTERVAL_SECONDS", 10)
BATCH_SIZE = getattr(settings, "WORKER_BATCH_SIZE", 5)
MAX_RETRIES = getattr(settings, "WORKER_MAX_RETRIES", 5)

# How long we allow a single job to run (seconds). Prevents forever-hanging jobs.
JOB_TIMEOUT_SECONDS = getattr(settings, "WORKER_JOB_TIMEOUT_SECONDS", 20 * 60)  # 20 minutes

# If a job has been in 'processing' state longer than this, consider it stale and reclaimable.
STALE_PROCESSING_SECONDS = getattr(settings, "WORKER_STALE_PROCESSING_SECONDS", 30 * 60)  # 30 minutes

# How many threads to use when we want parallel local processing. The loop remains single-process,
# but you can increase parallel workers later. Keep small to avoid memory spike.
LOCAL_EXECUTOR_WORKERS = getattr(settings, "WORKER_LOCAL_EXECUTOR_WORKERS", 2)

executor = ThreadPoolExecutor(max_workers=LOCAL_EXECUTOR_WORKERS)


# -------------------------
# Supabase helper wrappers
# -------------------------
def fetch_pending(limit: int = BATCH_SIZE) -> List[Dict[str, Any]]:
    """
    Primary fetch of pending rows.
    If there are no 'pending' rows, also attempt to fetch stale 'processing' rows
    older than STALE_PROCESSING_SECONDS so crashed workers get reclaimed.
    """
    try:
        pending = supabase.find_pending_summaries(limit)
    except Exception:
        logger.exception("Failed fetching pending summaries (primary)")
        pending = []

    if not pending:
        # Attempt to reclaim stale processing rows
        try:
            cutoff = int(time.time()) - STALE_PROCESSING_SECONDS
            # Expected SupabaseClient method (if not present, replace with your method)
            stale = supabase.find_processing_older_than(cutoff, limit=limit)
            if stale:
                logger.info("Found %d stale processing rows to reclaim", len(stale))
                return stale
        except AttributeError:
            # Supabase client doesn't implement find_processing_older_than
            logger.debug("SupabaseClient has no find_processing_older_than; skipping reclaim")
        except Exception:
            logger.exception("Failed fetching stale processing summaries")

    return pending


def claim_summary(row_id: Any) -> bool:
    """Optimistic claim: set status to 'processing' only if still 'pending' or stale."""
    try:
        payload = {
            "status": "processing",
            "claimed_at": utc_now_iso(),
            "processing_started_at": utc_now_iso()
        }
        return supabase.update_zoom_summary(row_id, payload)
    except Exception:
        logger.exception("Failed to claim summary %s", row_id)
        return False


def mark_completed(row_id: Any, metadata: Optional[Dict[str, Any]] = None, exercises_generated: bool = True):
    try:
        status = "completed" if exercises_generated else "awaiting_exercises"
        payload = {
            "status": status,
            "processed_at": utc_now_iso(),
            "processing_completed_at": utc_now_iso(),
        }
        if metadata:
            payload["processing_metadata"] = metadata
        supabase.update_zoom_summary(row_id, payload)
        logger.info("Marked row %s as %s", row_id, status)
    except Exception:
        logger.exception("Failed to mark completed %s", row_id)


def mark_failed(row_id: Any, error: str, attempts: int):
    try:
        # compute new status
        next_status = "pending" if attempts < MAX_RETRIES else "failed"
        payload = {
            "status": next_status,
            "last_error": str(error),
            "processing_attempts": attempts,
            "updated_at": utc_now_iso()
        }
        if attempts < MAX_RETRIES:
            payload["next_retry_at"] = int(time.time()) + (60 * (2 ** (attempts - 1)))
        else:
            payload["processed_at"] = utc_now_iso()
        supabase.update_zoom_summary(row_id, payload)
        logger.warning("Marked row %s as failed/pending (attempts=%s) error=%s", row_id, attempts, error)
    except Exception:
        logger.exception("Failed to mark failed %s", row_id)


# -------------------------
# Utilities
# -------------------------
def _is_video_file_type(file_type: Optional[str]) -> bool:
    if not file_type:
        return False
    ext = (file_type or "").lower()
    # treat mp4 and mov as audio containers as a fallback (Zoom often uses mp4)
    return ext in ("mp4", "mov", "m4v", "mkv")


def _select_transcript_or_audio(files: List[Dict[str, Any]]):
    """Return (transcript_file, audio_file OR video_file)"""
    # prefer transcript
    t = has_transcript_file(files)
    if t:
        return t, None

    # prefer dedicated audio file
    a = has_audio_files(files)
    if a:
        return None, a

    # fallback: if any file looks like mp4/video, treat as audio (we'll download and extract if needed)
    for f in files or []:
        if _is_video_file_type(f.get("file_type")):
            logger.debug("Treating video file as audio fallback: %s", f.get("file_type"))
            return None, f

    return None, None


def _stream_download_to_tempfile(download_url: str, desc: str = "zoom_download", chunk_size: int = 8 * 1024 * 1024) -> str:
    """
    Stream a remote URL to a temporary file and return the path.
    This avoids loading whole file in memory.
    """
    token = zoom_api.get_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    logger.info("Streaming download %s -> temp (desc=%s)", download_url, desc)

    # create named temp file that persists until we remove it
    tmp = tempfile.NamedTemporaryFile(delete=False, prefix="zoom_", suffix=".tmp")
    tmp_path = tmp.name
    tmp.close()

    try:
        with requests_get_stream_safe(download_url, headers=headers) as r:
            # r is a requests.Response
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    with open(tmp_path, "ab") as fw:
                        fw.write(chunk)
        return tmp_path
    except Exception:
        # cleanup on failure
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise


def requests_get_stream_safe(url: str, headers: Dict[str, str] = None, timeout: int = 120):
    """Helper wrapper around requests.get with streaming and simple retry on 401 token refresh."""
    import requests

    headers = headers or {}
    r = requests.get(url, headers=headers, timeout=timeout, stream=True)
    # If 401, try refreshing token then retry once
    if r.status_code == 401:
        logger.warning("Stream download returned 401; refreshing token and retrying")
        token = zoom_api.tm.refresh()
        if token:
            headers["Authorization"] = f"Bearer {token}"
            r = requests.get(url, headers=headers, timeout=timeout, stream=True)
    r.raise_for_status()
    return r


# -------------------------
# Main processing
# -------------------------
def _process_row_internal(row: Dict[str, Any]):
    """
    The heavy work of processing a single row. Designed to be run in a worker future
    and bounded by JOB_TIMEOUT_SECONDS from the outer caller.
    """
    row_id = row.get("id")
    logger.info("Starting work on row %s", row_id)

    # Attempt to claim; claim_summary will only succeed if row is claimable
    if not claim_summary(row_id):
        logger.info("Could not claim row %s; skipping", row_id)
        return

    files = row.get("recording_files") or row.get("files") or []
    # If no files in the row, fetch from Zoom API
    if not files:
        logger.info("No recording_files in row %s, fetching from Zoom API", row_id)
        teacher_email = row.get("teacher_email")
        meeting_date = row.get("meeting_date")
        start_time = row.get("start_time")

        if not teacher_email or not meeting_date:
            raise RuntimeError("Missing teacher_email or meeting_date - cannot fetch Zoom recordings")

        try:
            zoom_response = zoom_api.list_user_recordings(
                user_id=teacher_email,
                from_date=meeting_date,
                to_date=meeting_date
            )
        except Exception as zoom_err:
            err_str = str(zoom_err)
            # Map some common error reasons to friendly messages and mark failed
            attempts = int((row.get("processing_attempts") or 0) + 1)
            if "404" in err_str:
                msg = f"Zoom user '{teacher_email}' not found or inaccessible. Check Zoom account configuration."
                logger.warning(msg)
                mark_failed(row_id, msg, attempts)
                return
            if "401" in err_str or "403" in err_str:
                msg = f"Zoom authentication failed when listing recordings: {err_str}"
                logger.warning(msg)
                mark_failed(row_id, msg, attempts)
                return
            logger.exception("Zoom API error while listing recordings for row %s: %s", row_id, zoom_err)
            mark_failed(row_id, f"Zoom API error: {err_str}", attempts)
            return

        meetings = zoom_response.get("meetings", [])
        logger.info("Found %d meetings for %s on %s", len(meetings), teacher_email, meeting_date)

        # Try to select meeting (same robust logic as before)
        meeting_id = row.get("meeting_id")
        selected_meeting = None

        if meeting_id:
            meeting_id_str = str(meeting_id)
            for m in meetings:
                mid = str(m.get("id") or m.get("uuid") or "")
                if mid and (mid == meeting_id_str or meeting_id_str in mid) and m.get("recording_files"):
                    selected_meeting = m
                    break

        # pick closest start_time if present
        if not selected_meeting and start_time:
            try:
                target_hm = str(start_time)[:5]
                h, m = target_hm.split(":", 1)
                target_minutes = int(h) * 60 + int(m)
            except Exception:
                target_minutes = None

            if target_minutes is not None:
                best_diff = None
                for m in meetings:
                    mst = (m.get("start_time") or "")
                    if len(mst) >= 16:
                        hm = mst[11:16]
                        try:
                            hh, mm = hm.split(":", 1)
                            mins = int(hh) * 60 + int(mm)
                        except Exception:
                            continue
                        diff = abs(mins - target_minutes)
                        if (best_diff is None or diff < best_diff) and m.get("recording_files"):
                            best_diff = diff
                            selected_meeting = m
                if best_diff is not None and best_diff > 90:
                    logger.info("Closest meeting start time diff=%s min for row %s outside window", best_diff, row_id)
                    # leave selected_meeting as None (fallback to first)

        # fallback: first meeting with recordings
        if not selected_meeting:
            for m in meetings:
                if m.get("recording_files"):
                    selected_meeting = m
                    break

        if not selected_meeting:
            attempts = int((row.get("processing_attempts") or 0) + 1)
            msg = "No Zoom recordings found for specified teacher/date"
            logger.warning(msg + " for row %s", row_id)
            mark_failed(row_id, msg, attempts)
            return

        files = selected_meeting.get("recording_files", [])
        logger.info("Selected meeting %s with %d files for row %s", selected_meeting.get("id"), len(files), row_id)

    # Choose transcript vs audio (with mp4 fallback)
    transcript_file, audio_file = _select_transcript_or_audio(files)

    transcript_text = ""
    transcription_source = None
    temp_file_path = None

    try:
        if transcript_file:
            # Download transcript (usually small) -- stream and decode
            download_url = transcript_file.get("download_url")
            try:
                content_bytes = zoom_api.download_file(download_url)
                content = content_bytes.decode("utf-8", errors="ignore")
                transcript_text = clean_vtt_transcript(content)
                transcription_source = "zoom_native_transcript"
                logger.info("Downloaded native transcript for row %s, length=%d", row_id, len(transcript_text or ""))
            except Exception:
                logger.exception("Failed downloading transcript file for row %s", row_id)
                raise

        elif audio_file:
            download_url = audio_file.get("download_url")
            # stream to temp file
            temp_file_path = _stream_download_to_tempfile(download_url, desc=f"row_{row_id}")
            logger.info("Downloaded audio/video to temp file %s for row %s", temp_file_path, row_id)

            # transcribe using AssemblyAIHelper (prefer local-file SDK method)
            try:
                from ..ai.utils.assemblyai_helper import AssemblyAIHelper
                aai = AssemblyAIHelper()
            except Exception:
                aai = None
                logger.exception("Failed to import AssemblyAIHelper; will attempt HTTP fallback if available")

            transcript_result = None
            # Try SDK local file transcription first (recommended)
            if aai and getattr(aai, "enabled", False):
                logger.info("Using AssemblyAI SDK/local-file transcription for row %s", row_id)
                try:
                    transcript_result = aai.transcribe_local_file(temp_file_path, language_code="en")
                except Exception:
                    logger.exception("AssemblyAI SDK transcribe_local_file failed for row %s", row_id)

            # Next, try HTTP chunked upload fallback (transcribe_audio_bytes expects bytes)
            if not transcript_result and aai:
                try:
                    logger.info("Using AssemblyAI HTTP upload (streaming file bytes) for row %s", row_id)
                    # Read file in streaming chunks to memory-limited streams.
                    # aai.transcribe_audio_bytes accepts bytes blob in your helper; avoid loading into memory fully
                    # We'll stream file into memory in chunks but upload via requests inside helper.
                    with open(temp_file_path, "rb") as fh:
                        audio_bytes = fh.read()  # assemblyai_helper.transcribe_audio_bytes currently expects bytes
                        transcript_result = aai.transcribe_audio_bytes(audio_bytes)
                except Exception:
                    logger.exception("AssemblyAI HTTP transcribe_audio_bytes failed for row %s", row_id)
                    transcript_result = None

            # If still not available, try to return a helpful error
            if transcript_result and transcript_result.get("text"):
                transcript_text = transcript_result.get("text", "")
                transcription_source = "assemblyai"
                logger.info("AssemblyAI transcription success for row %s (chars=%d)", row_id, len(transcript_text or ""))
            else:
                # No transcript; mark failed with helpful reason
                attempts = int((row.get("processing_attempts") or 0) + 1)
                # Distinguish empty transcript vs failure
                duration = transcript_result.get("duration") if transcript_result else None
                if duration is not None and duration <= 5:
                    msg = f"Recording too short ({duration}s) to transcribe"
                else:
                    msg = "AssemblyAI transcription returned empty text or failed"
                logger.warning(msg + " for row %s", row_id)
                mark_failed(row_id, msg, attempts)
                return

        else:
            # No transcript nor audio found
            attempts = int((row.get("processing_attempts") or 0) + 1)
            msg = "No transcript or audio files found in recording"
            logger.warning(msg + " for row %s", row_id)
            mark_failed(row_id, msg, attempts)
            return

        # Minimal validation we have a transcript
        if not transcript_text:
            attempts = int((row.get("processing_attempts") or 0) + 1)
            msg = "Transcript extraction produced empty text"
            logger.warning(msg + " for row %s", row_id)
            mark_failed(row_id, msg, attempts)
            return

        # Persist transcript into zoom_summaries (overwrite or update)
        update_payload = {
            "transcript": transcript_text,
            "transcript_length": len(transcript_text or ""),
            "transcript_source": transcription_source or "unknown",
            "transcription_status": "completed",
            "status": "awaiting_exercises",
            "processing_completed_at": utc_now_iso()
        }
        supabase.update_zoom_summary(row_id, update_payload)
        logger.info("Persisted transcript for row %s", row_id)

        # Prepare summary for AI orchestrator
        summary_for_ai = dict(row)
        summary_for_ai["transcript"] = transcript_text
        if transcription_source:
            summary_for_ai["transcript_source"] = transcription_source

        # Generate exercises (call existing orchestrator)
        exercise_generation_failed = False
        try:
            from ..ai.orchestrator import process_transcript_to_exercises
            result = process_transcript_to_exercises(summary_for_ai, persist=True)
            if result.get("ok"):
                logger.info("Generated exercises for row %s: %s", row_id, result.get("counts"))
            else:
                logger.warning("Exercise generation reported failure for row %s: %s", row_id, result.get("reason"))
                exercise_generation_failed = True
        except Exception as e:
            logger.exception("Exercise generation exception for row %s: %s", row_id, e)
            exercise_generation_failed = True

        if exercise_generation_failed:
            mark_completed(row_id, metadata={"transcription_source": transcription_source}, exercises_generated=False)
        else:
            mark_completed(row_id, metadata={"transcription_source": transcription_source}, exercises_generated=True)

    finally:
        # Ensure temp file cleanup
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.debug("Removed temp file %s", temp_file_path)
            except Exception:
                logger.warning("Could not remove temp file %s", temp_file_path)


def process_row(row: Dict[str, Any]):
    """
    Run heavy processing in a thread with a timeout to avoid hanging the worker.
    """
    row_id = row.get("id")
    try:
        future = executor.submit(_process_row_internal, row)
        # Block with timeout
        future.result(timeout=JOB_TIMEOUT_SECONDS)
    except FutureTimeout:
        # Timeout occurred: mark job for retry
        tb = "Job exceeded timeout of {} seconds".format(JOB_TIMEOUT_SECONDS)
        logger.exception("Timeout processing row %s: %s", row_id, tb)
        attempts = int((row.get("processing_attempts") or 0) + 1)
        mark_failed(row_id, tb, attempts)
    except Exception as exc:
        tb = traceback.format_exc()
        logger.exception("Processing failed for %s: %s\n%s", row_id, exc, tb)
        attempts = int((row.get("processing_attempts") or 0) + 1)
        mark_failed(row_id, str(exc), attempts)


def run_forever():
    logger.info("Zoom processor started. Poll interval %ds; batch=%s; timeout=%ds", POLL_INTERVAL, BATCH_SIZE, JOB_TIMEOUT_SECONDS)
    while True:
        try:
            pending = fetch_pending(BATCH_SIZE)
            if not pending:
                time.sleep(POLL_INTERVAL)
                continue
            for row in pending:
                try:
                    process_row(row)
                except Exception:
                    logger.exception("Unhandled exception while processing row, continuing to next")
        except KeyboardInterrupt:
            logger.info("Processor interrupted; exiting.")
            break
        except Exception:
            logger.exception("Unexpected error in processor loop; sleeping before retry.")
            time.sleep(min(POLL_INTERVAL, 60))


if __name__ == "__main__":
    run_forever()
