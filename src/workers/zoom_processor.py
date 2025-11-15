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

def mark_completed(row_id: Any, metadata: Optional[Dict[str, Any]] = None):
    try:
        payload = {"status": "completed", "processed_at": utc_now_iso()}
        if metadata:
            payload["processing_metadata"] = metadata
        supabase.update_zoom_summary(row_id, payload)
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

        # Determine best available file to fetch
        files = row.get("recording_files") or row.get("files") or []
        transcript_file = has_transcript_file(files)
        audio_file = has_audio_files(files)

        transcript_text = ""
        transcription_source = None

        if transcript_file:
            download_url = transcript_file.get("download_url")
            try:
                content_bytes = zoom_api.download_file(download_url)
                content = content_bytes.decode("utf-8", errors="ignore")
                transcript_text = clean_vtt_transcript(content)
                transcription_source = "zoom_native_transcript"
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
                    logger.info("Transcribing audio with AssemblyAI for row %s", row_id)
                    result = aai_helper.transcribe_audio(download_url)
                    if result and result.get('text'):
                        transcript_text = result['text']
                        transcription_source = "assemblyai"
                        logger.info("AssemblyAI transcription completed: %d chars", len(transcript_text))
                    else:
                        logger.warning("AssemblyAI transcription failed for row %s", row_id)
                        transcription_source = "audio_file_no_transcript"
                else:
                    logger.warning("AssemblyAI not available, downloading audio only")
                    audio_bytes = zoom_api.download_file(download_url)
                    transcription_source = "audio_file_downloaded"
            except Exception:
                logger.exception("Failed processing audio for row %s", row_id)
                raise
        else:
            logger.warning("No transcript or audio found for row %s", row_id)
            raise RuntimeError("No transcript or audio available")

        # Minimal validation
        if not transcript_text and transcription_source != "audio_file_downloaded":
            raise RuntimeError("Transcript extraction failed or empty")

        # Persist transcript into zoom_summaries (overwrite or update)
        update_payload = {
            "transcript": transcript_text,
            "transcript_length": len(transcript_text or ""),
            "transcript_source": transcription_source or "unknown",
            "transcription_status": "completed" if transcript_text else "pending",
            "processing_completed_at": utc_now_iso()
        }
        supabase.update_zoom_summary(row_id, update_payload)

        # Call AI orchestrator to generate exercises
        try:
            from ..ai.orchestrator import process_transcript_to_exercises
            result = process_transcript_to_exercises(row, persist=True)
            if result.get("ok"):
                logger.info("Generated exercises for row %s: %s", row_id, result.get("counts"))
            else:
                logger.warning("Exercise generation failed for row %s: %s", row_id, result.get("reason"))
        except Exception as e:
            logger.exception("Failed to generate exercises for row %s: %s", row_id, e)

        mark_completed(row_id, metadata={"transcription_source": transcription_source})
        logger.info("Processed and marked completed %s", row_id)

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
