# src/workers/zoom_processor.py
import logging
import time
import traceback
from typing import Dict, Any, Optional
from ..db.supabase_client import SupabaseClient
from ..zoom.zoom_utils import has_transcript_file, has_audio_files, clean_vtt_transcript
from ..zoom.zoom_client import ZoomAPI
from ..config import settings
from ..time_utils import utc_now_iso

logger = logging.getLogger(__name__)

supabase = SupabaseClient()
zoom_api = ZoomAPI()

POLL_INTERVAL = settings.WORKER_POLL_INTERVAL_SECONDS
BATCH_SIZE = settings.WORKER_BATCH_SIZE
MAX_RETRIES = settings.WORKER_MAX_RETRIES

def fetch_pending(limit: int = BATCH_SIZE):
    try:
        return supabase.find_pending_summaries(limit)
    except Exception:
        logger.exception("Failed fetching pending summaries")
        return []

def claim_summary(row_id: Any) -> bool:
    """Optimistic claim: set status to 'processing' only if still 'pending'."""
    try:
        payload = {"status": "processing", "claimed_at": utc_now_iso()}
        return supabase.update_zoom_summary(row_id, payload)
    except Exception:
        logger.exception("Failed to claim summary %s", row_id)
        return False

def mark_completed(row_id: Any, metadata: Optional[Dict[str, Any]] = None, exercises_generated: bool = True):
    try:
        status = "completed" if exercises_generated else "awaiting_exercises"
        payload = {"status": status, "processed_at": utc_now_iso()}
        if metadata:
            payload["processing_metadata"] = metadata
        supabase.update_zoom_summary(row_id, payload)
        logger.info(f"Marked row {row_id} as {status}")
    except Exception:
        logger.exception("Failed to mark completed %s", row_id)

def mark_failed(row_id: Any, error: str, attempts: int):
    try:
        payload = {
            "status": "pending" if attempts < MAX_RETRIES else "failed",
            "last_error": error,
            "processing_attempts": attempts,
            "updated_at": utc_now_iso()
        }
        if attempts < MAX_RETRIES:
            # backoff field for consumers
            payload["next_retry_at"] = int(time.time()) + (60 * (2 ** (attempts - 1)))
        else:
            payload["processed_at"] = utc_now_iso()
        supabase.update_zoom_summary(row_id, payload)
    except Exception:
        logger.exception("Failed to mark failed %s", row_id)

def process_row(row: Dict[str, Any]):
    row_id = row.get("id")
    try:
        if not claim_summary(row_id):
            logger.debug("Could not claim row %s", row_id)
            return

        # Fetch recording files from Zoom if not already present
        files = row.get("recording_files") or row.get("files") or []
        
        if not files:
            logger.info("No recording_files in row %s, fetching from Zoom API", row_id)
            teacher_email = row.get("teacher_email")
            meeting_date = row.get("meeting_date")
            start_time = row.get("start_time")
            end_time = row.get("end_time")
            
            if not teacher_email or not meeting_date:
                raise RuntimeError("Missing teacher_email or meeting_date - cannot fetch Zoom recordings")
            
            try:
                # Fetch recordings from Zoom API
                try:
                    zoom_response = zoom_api.list_user_recordings(
                        user_id=teacher_email,
                        from_date=meeting_date,
                        to_date=meeting_date
                    )
                except Exception as zoom_err:
                    err_str = str(zoom_err)
                    # Handle specific HTTP errors with cleaner messages (no stack trace)
                    if "404" in err_str:
                        logger.warning(
                            f"Zoom user not found for row {row_id}: '{teacher_email}' does not exist in your Zoom account or has no recording access."
                        )
                        logger.info(
                            "METRIC:zoom_user_not_found user=%s row=%s",
                            teacher_email,
                            row_id,
                        )
                        mark_failed(
                            row_id,
                            f"Zoom user '{teacher_email}' not found. Verify this email exists in your Zoom account with cloud recording permissions.",
                            int((row.get("processing_attempts") or 0) + 1)
                        )
                    elif "401" in err_str or "403" in err_str:
                        logger.warning(f"Zoom authentication failed for row {row_id}: {err_str}")
                        logger.info(
                            "METRIC:zoom_auth_error user=%s row=%s",
                            teacher_email,
                            row_id,
                        )
                        mark_failed(
                            row_id,
                            f"Zoom authentication failed. Check ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET, and ZOOM_ACCOUNT_ID in .env.",
                            int((row.get("processing_attempts") or 0) + 1)
                        )
                    elif "getaddrinfo failed" in err_str or "NameResolutionError" in err_str:
                        logger.warning(f"Network/DNS error for row {row_id}: Cannot reach api.zoom.us. Check your internet connection.")
                        logger.info(
                            "METRIC:zoom_network_error user=%s row=%s",
                            teacher_email,
                            row_id,
                        )
                        mark_failed(
                            row_id,
                            f"Network error: Cannot reach Zoom API. Check internet/DNS connectivity.",
                            int((row.get("processing_attempts") or 0) + 1)
                        )
                    else:
                        logger.exception(f"Zoom API call failed for row {row_id}: {zoom_err}")
                        mark_failed(
                            row_id,
                            f"Failed to fetch recordings from Zoom API: {err_str}. Check Zoom credentials and API access.",
                            int((row.get("processing_attempts") or 0) + 1)
                        )
                    return
                
                meetings = zoom_response.get("meetings", [])
                logger.info(f"Found {len(meetings)} meetings for {teacher_email} on {meeting_date}")

                # Try to select the *correct* meeting in a robust way:
                # 1) If meeting_id is known, prefer an exact/partial ID match.
                # 2) Otherwise, if start_time is provided, pick the meeting whose start time-of-day
                #    (HH:MM) is closest to the expected start_time, within a reasonable window.
                # 3) Fallback: first meeting that has any recording_files (previous behaviour).
                matching_meeting = None
                meeting_id = row.get("meeting_id")

                # 1) Exact meeting_id match if available
                if meeting_id:
                    meeting_id_str = str(meeting_id)
                    for m in meetings:
                        mid = str(m.get("id") or m.get("uuid") or "")
                        if not mid:
                            continue
                        if mid == meeting_id_str or meeting_id_str in mid:
                            if m.get("recording_files"):
                                matching_meeting = m
                                logger.info(
                                    "Selected meeting by meeting_id match for row %s: id=%s topic=%s",
                                    row_id,
                                    mid,
                                    m.get("topic"),
                                )
                                break

                # 2) If no meeting_id match, try closest start time-of-day
                if not matching_meeting and start_time:
                    # start_time comes from backend as HH:MM or HH:MM:SS; normalise to HH:MM
                    target_hm = str(start_time)[:5]
                    target_minutes = None
                    try:
                        h, m = target_hm.split(":", 1)
                        target_minutes = int(h) * 60 + int(m)
                    except Exception:
                        logger.debug("Could not parse start_time '%s' for row %s", start_time, row_id)

                    if target_minutes is not None:
                        best_diff = None
                        best_meeting = None
                        for m in meetings:
                            mst = (m.get("start_time") or "")
                            # Zoom start_time is ISO-8601; extract HH:MM from the time part
                            if len(mst) >= 16:
                                hm = mst[11:16]
                                try:
                                    hh, mm = hm.split(":", 1)
                                    mins = int(hh) * 60 + int(mm)
                                except Exception:
                                    continue
                                diff = abs(mins - target_minutes)
                                if best_diff is None or diff < best_diff:
                                    if m.get("recording_files"):
                                        best_diff = diff
                                        best_meeting = m

                        # Only accept if within a reasonable window (e.g. +/- 90 minutes)
                        if best_meeting is not None:
                            if best_diff is not None and best_diff <= 90:
                                matching_meeting = best_meeting
                                logger.info(
                                    "Selected meeting by closest start time for row %s (diff=%s min): %s",
                                    row_id,
                                    best_diff,
                                    best_meeting.get("start_time"),
                                )
                            else:
                                logger.info(
                                    "Closest meeting start time diff=%s min for row %s is outside window; "
                                    "falling back to first recording.",
                                    best_diff,
                                    row_id,
                                )

                # 3) Fallback: first meeting with any recording_files
                if not matching_meeting:
                    for meeting in meetings:
                        if meeting.get("recording_files"):
                            matching_meeting = meeting
                            logger.info(
                                "Selected first meeting with recordings as fallback for row %s: %s",
                                row_id,
                                meeting.get("topic"),
                            )
                            break
                
                if matching_meeting:
                    files = matching_meeting.get("recording_files", [])
                    logger.info(f"Found {len(files)} recording files for row {row_id}")
                else:
                    # No recordings found - mark as failed with helpful message
                    logger.warning(f"No Zoom recordings found for {teacher_email} on {meeting_date}")
                    logger.info(
                        "METRIC:zoom_no_recordings user=%s date=%s row=%s",
                        teacher_email,
                        meeting_date,
                        row_id,
                    )
                    mark_failed(
                        row_id, 
                        f"No Zoom recordings available for {teacher_email} on {meeting_date}. Recording may not be ready yet or recording was not enabled for this meeting.",
                        int((row.get("processing_attempts") or 0) + 1)
                    )
                    return
                    
            except Exception as e:
                logger.exception(f"Failed to fetch Zoom recordings for row {row_id}: {e}")
                raise
        
        transcript_file = has_transcript_file(files)
        audio_file = has_audio_files(files)
        
        # Log what files we found for debugging
        logger.info(
            "Row %s: Found %d recording files. Transcript file: %s, Audio file: %s",
            row_id,
            len(files),
            transcript_file.get('recording_type') if transcript_file else None,
            audio_file.get('recording_type') if audio_file else None,
        )
        if audio_file:
            file_size = audio_file.get('file_size', 0)
            logger.info(
                "Row %s: Audio file size=%s bytes, type=%s",
                row_id,
                file_size,
                audio_file.get('file_type'),
            )

        transcript_text = ""
        transcription_source = None

        if transcript_file:
            download_url = transcript_file.get("download_url")
            try:
                content_bytes = zoom_api.download_file(download_url)
                content = content_bytes.decode("utf-8", errors="ignore")
                transcript_text = clean_vtt_transcript(content)
                transcription_source = "zoom_native_transcript"
                logger.info(
                    "METRIC:transcription_success source=zoom_native row=%s length=%s",
                    row_id,
                    len(transcript_text or ""),
                )
            except Exception:
                logger.exception("Failed downloading transcript file for row %s", row_id)
                raise

        elif audio_file:
            # Use AssemblyAI for audio transcription
            download_url = audio_file.get("download_url")
            try:
                from ..ai.utils.assemblyai_helper import AssemblyAIHelper
                aai_helper = AssemblyAIHelper()
                
                if aai_helper.enabled:
                    logger.info("Downloading audio with Zoom auth for row %s", row_id)
                    # Download audio using authenticated Zoom client
                    audio_bytes = zoom_api.download_file(download_url)
                    logger.info("Downloaded %d bytes, uploading to AssemblyAI for row %s", len(audio_bytes), row_id)
                    
                    # Upload bytes to AssemblyAI for transcription
                    result = aai_helper.transcribe_audio_bytes(audio_bytes)
                    if result and result.get('text'):
                        transcript_text = result['text']
                        transcription_source = "assemblyai"
                        logger.info("AssemblyAI transcription completed: %d chars", len(transcript_text))
                        logger.info(
                            "METRIC:transcription_success source=assemblyai row=%s length=%s",
                            row_id,
                            len(transcript_text or ""),
                        )
                    else:
                        duration = result.get('duration') if result else None
                        logger.warning(
                            "AssemblyAI transcription returned empty text for row %s (audio duration=%ss). "
                            "This usually means the recording is too short or has no clear speech.",
                            row_id,
                            duration,
                        )
                        # Provide a clear, user-facing reason in last_error so the backend can see why
                        # this lesson cannot produce a transcript or exercises.
                        attempts = int((row.get("processing_attempts") or 0) + 1)
                        if duration is not None and duration <= 5:
                            logger.info(
                                "METRIC:transcription_too_short row=%s duration=%s",
                                row_id,
                                duration,
                            )
                            error_msg = (
                                f"Recording too short ({duration}s). Not enough speech to generate a transcript "
                                "or exercises. This is usually a quick test or accidental join."
                            )
                        else:
                            logger.info(
                                "METRIC:transcription_empty_text row=%s duration=%s",
                                row_id,
                                duration,
                            )
                            error_msg = (
                                "AssemblyAI transcription returned empty text. "
                                "Check that the Zoom recording has clear speech and is not silent."
                            )
                        mark_failed(row_id, error_msg, attempts)
                        transcription_source = "audio_file_no_transcript"
                        return
                else:
                    logger.warning("AssemblyAI not available, downloading audio only")
                    audio_bytes = zoom_api.download_file(download_url)
                    transcription_source = "audio_file_downloaded"
            except Exception:
                logger.exception("Failed processing audio for row %s", row_id)
                raise
        else:
            # No transcript or audio files in the recording
            logger.warning("No transcript or audio files found in recording for row %s", row_id)
            logger.info("METRIC:zoom_recording_no_audio row=%s", row_id)
            mark_failed(
                row_id,
                "Zoom recording exists but contains no transcript or audio files. Recording may still be processing.",
                int((row.get("processing_attempts") or 0) + 1)
            )
            return

        # Minimal validation - we must have a non-empty transcript
        if not transcript_text:
            logger.warning("Transcript extraction resulted in empty text for row %s", row_id)
            logger.info("METRIC:transcription_empty_text_generic row=%s", row_id)
            mark_failed(
                row_id,
                "Transcript extraction failed or resulted in empty text. This usually means the recording "
                "contained no speech or only a few seconds of audio.",
                int((row.get("processing_attempts") or 0) + 1)
            )
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

        # Prepare a summary row for the AI orchestrator that already contains the transcript
        summary_for_ai = dict(row)
        summary_for_ai["transcript"] = transcript_text
        if transcription_source:
            summary_for_ai["transcript_source"] = transcription_source

        # Call AI orchestrator to generate exercises
        exercise_generation_failed = False
        try:
            from ..ai.orchestrator import process_transcript_to_exercises
            result = process_transcript_to_exercises(summary_for_ai, persist=True)
            if result.get("ok"):
                logger.info("Generated exercises for row %s: %s", row_id, result.get("counts"))
            else:
                logger.warning("Exercise generation failed for row %s: %s", row_id, result.get("reason"))
                exercise_generation_failed = True
        except Exception as e:
            logger.exception("Failed to generate exercises for row %s: %s", row_id, e)
            exercise_generation_failed = True
        
        # Mark as completed if exercises generated, otherwise awaiting_exercises
        if exercise_generation_failed:
            logger.warning("Exercise generation failed for row %s - marking as awaiting_exercises", row_id)
            mark_completed(row_id, metadata={"transcription_source": transcription_source}, exercises_generated=False)
        else:
            logger.info("Successfully generated exercises for row %s", row_id)
            mark_completed(row_id, metadata={"transcription_source": transcription_source}, exercises_generated=True)

    except Exception as exc:
        tb = traceback.format_exc()
        logger.exception("Processing failed for %s: %s\n%s", row_id, exc, tb)
        attempts = int((row.get("processing_attempts") or 0) + 1)
        mark_failed(row_id, str(exc), attempts)

def run_forever():
    logger.info("Zoom processor started. Poll interval %ds", POLL_INTERVAL)
    while True:
        try:
            pending = fetch_pending(BATCH_SIZE)
            if not pending:
                time.sleep(POLL_INTERVAL)
                continue
            for row in pending:
                process_row(row)
        except KeyboardInterrupt:
            logger.info("Processor interrupted; exiting.")
            break
        except Exception:
            logger.exception("Unexpected error in processor loop; sleeping before retry.")
            time.sleep(min(POLL_INTERVAL, 60))

if __name__ == "__main__":
    run_forever()
