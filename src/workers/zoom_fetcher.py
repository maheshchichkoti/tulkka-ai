# src/workers/zoom_fetcher.py
import logging
import time
from typing import List, Dict, Any
from ..config import settings
from ..zoom.zoom_client import ZoomAPI
from ..db.supabase_client import SupabaseClient
from ..time_utils import utc_now_iso

logger = logging.getLogger(__name__)

zoom_api = ZoomAPI()
supabase = SupabaseClient()

POLL_INTERVAL = settings.WORKER_POLL_INTERVAL_SECONDS
BATCH_SIZE = settings.WORKER_BATCH_SIZE

def recording_exists(meeting_id: str, meeting_date: str) -> bool:
    try:
        row = supabase.fetch_zoom_summary(meeting_id=meeting_id, meeting_date=meeting_date)
        return bool(row)
    except Exception:
        return False

def insert_pending_recording(meeting: Dict[str, Any]):
    row = {
        "meeting_id": meeting.get("id") or meeting.get("uuid"),
        "meeting_topic": meeting.get("topic"),
        "teacher_email": meeting.get("host_email") or meeting.get("host"),
        "start_time": meeting.get("start_time"),
        "meeting_date": meeting.get("start_time"),
        "recording_files": meeting.get("recording_files", []),
        "status": "pending",
        "processing_attempts": 0,
        "created_at": utc_now_iso()
    }
    try:
        supabase.insert_zoom_summary(row)
        logger.info("Inserted pending summary %s", row["meeting_id"])
    except Exception:
        logger.exception("Failed to insert pending recording")

def process_zoom_feed():
    # Basic fetch of recordings for 'me' - adapt to your tenant (list users if needed)
    try:
        # For production, list teacher users and fetch for each. Here using current account user_id "me".
        meetings = zoom_api.list_user_recordings("me", from_date="1970-01-01", to_date=utc_now_iso()[:10]).get("meetings", [])
        logger.info("Fetched %d meetings from Zoom", len(meetings))
    except Exception:
        logger.exception("Zoom fetch failed")
        return

    for m in meetings:
        mid = m.get("id") or m.get("uuid")
        start = m.get("start_time")
        if not mid or not start:
            continue
        if recording_exists(mid, start):
            logger.debug("Recording exists, skipping %s", mid)
            continue
        insert_pending_recording(m)

def run_forever():
    logger.info("Zoom fetcher started, poll interval %ds", POLL_INTERVAL)
    while True:
        try:
            process_zoom_feed()
        except Exception:
            logger.exception("Error in fetcher loop")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run_forever()
