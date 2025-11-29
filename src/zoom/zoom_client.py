# src/zoom/zoom_client.py

import logging
import requests
import time
from typing import Optional, Dict, Any, List
from .zoom_auth import ZoomTokenManager

logger = logging.getLogger(__name__)


class ZoomAPI:
    BASE_URL = "https://api.zoom.us/v2"

    def __init__(self):
        self.tm = ZoomTokenManager()

    # -------------------------------------------------------------
    # Token Management
    # -------------------------------------------------------------
    def get_token(self) -> Optional[str]:
        if self.tm.is_valid():
            return self.tm.access_token
        return self.tm.refresh() or self.tm.access_token

    # -------------------------------------------------------------
    # Generic request helper with retries + error handling
    # -------------------------------------------------------------
    def _request(self, method: str, url: str, retries: int = 3, **kwargs):
        for attempt in range(1, retries + 1):
            token = self.get_token()
            headers = kwargs.pop("headers", {})
            headers["Authorization"] = f"Bearer {token}"

            try:
                resp = requests.request(method, url, headers=headers, timeout=20, **kwargs)

                # Retry on invalid token
                if resp.status_code == 401:
                    logger.warning("Zoom API returned 401, refreshing token...")
                    new_token = self.tm.refresh()
                    if new_token:
                        headers["Authorization"] = f"Bearer {new_token}"
                        resp = requests.request(method, url, headers=headers, timeout=20, **kwargs)

                # Retry on rate limit or server errors
                if resp.status_code in (429, 500, 503):
                    wait = 2 ** attempt
                    logger.warning(f"Zoom API error {resp.status_code}, retry {attempt}/{retries} after {wait}s")
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                return resp

            except requests.exceptions.RequestException as e:
                wait = 2 ** attempt
                logger.warning(f"Zoom request error {e}, retry {attempt}/{retries} after {wait}s")
                time.sleep(wait)

        raise RuntimeError(f"Zoom request failed after {retries} retries: {url}")

    # -------------------------------------------------------------
    # LIST USER RECORDINGS (supports pagination)
    # -------------------------------------------------------------
    def list_user_recordings(self, user_id: str, from_date: str, to_date: str) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/users/{user_id}/recordings"
        params = {"from": from_date, "to": to_date, "page_size": 100}

        all_meetings: List[Dict] = []
        next_token = None

        while True:
            if next_token:
                params["next_page_token"] = next_token

            resp = self._request("GET", url, params=params)
            data = resp.json()

            meetings = data.get("meetings", [])
            all_meetings.extend(meetings)

            next_token = data.get("next_page_token")
            if not next_token:
                break

        return {"meetings": all_meetings}

    # -------------------------------------------------------------
    # DOWNLOAD FILE (stream safe)
    # -------------------------------------------------------------
    def download_file(self, download_url: str) -> bytes:
        resp = self._request("GET", download_url, stream=True)

        # Stream download safely
        chunks = []
        for chunk in resp.iter_content(chunk_size=1024 * 512):  # 512KB chunks
            if chunk:
                chunks.append(chunk)

        return b"".join(chunks)
