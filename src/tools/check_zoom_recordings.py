import argparse
import logging
from typing import Any, Dict, List

from ..zoom.zoom_client import ZoomAPI
from ..zoom.zoom_utils import has_audio_files, has_transcript_file


logger = logging.getLogger(__name__)


def _print_meeting_summary(meetings: List[Dict[str, Any]], email: str, date: str) -> None:
    if not meetings:
        print(f"No Zoom meetings or recordings found for {email} on {date}.")
        return

    print(f"Found {len(meetings)} meeting(s) for {email} on {date}:")
    for idx, meeting in enumerate(meetings, start=1):
        topic = meeting.get("topic") or "(no topic)"
        start_time = meeting.get("start_time") or "unknown start_time"
        duration = meeting.get("duration")
        files = meeting.get("recording_files") or []
        audio_file = has_audio_files(files)
        transcript_file = has_transcript_file(files)

        print(
            f"- [{idx}] topic={topic!r}, start={start_time}, duration={duration} min, "
            f"files={len(files)}, has_audio={bool(audio_file)}, has_transcript={bool(transcript_file)}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check if a Zoom user (email) has cloud recordings for a given date.",
    )
    parser.add_argument(
        "--email",
        "-e",
        required=True,
        help="Teacher Zoom email (same value you pass as teacherEmail)",
    )
    parser.add_argument(
        "--date",
        "-d",
        required=True,
        help="Date to check (YYYY-MM-DD)",
    )

    args = parser.parse_args()
    email: str = args.email
    date: str = args.date

    api = ZoomAPI()

    try:
        resp = api.list_user_recordings(user_id=email, from_date=date, to_date=date)
    except Exception as exc:  # pragma: no cover - debug helper
        msg = str(exc)
        if "404" in msg:
            print(f"ERROR: Zoom user '{email}' not found or has no recording access.")
            print("Make sure this email exists in your Zoom account with cloud recording permissions.")
        elif "401" in msg or "403" in msg:
            print("ERROR: Zoom authentication failed.")
            print("Check ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET, and ZOOM_ACCOUNT_ID in your environment / .env.")
        elif "getaddrinfo failed" in msg or "NameResolutionError" in msg:
            print("ERROR: Network/DNS error when calling api.zoom.us.")
            print("Check your internet connection and DNS (for example: 'nslookup api.zoom.us').")
        else:
            print(f"ERROR calling Zoom API: {msg}")
        return 1

    meetings = resp.get("meetings", [])
    _print_meeting_summary(meetings, email, date)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(main())
