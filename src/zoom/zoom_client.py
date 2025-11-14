# src/zoom/zoom_client.py
import logging
from typing import Optional, Dict, Any
import requests
from .zoom_auth import ZoomTokenManager
from ..config import settings

logger = logging.getLogger(__name__)

class ZoomAPI:
    def __init__(self):
        self.tm = ZoomTokenManager()
        # if tokens present in env, keep them; refresh on demand

    def get_token(self) -> Optional[str]:
        # return currently valid token or attempt refresh
        if self.tm.is_valid():
            return self.tm.access_token
        return self.tm.refresh() or self.tm.access_token

    def list_user_recordings(self, user_id: str, from_date: str, to_date: str):
        token = self.get_token()
        if not token:
            raise RuntimeError("Zoom access token not available")
        url = f"https://api.zoom.us/v2/users/{user_id}/recordings"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"from": from_date, "to": to_date, "page_size": 100}
        r = requests.get(url, headers=headers, params=params, timeout=20)
        r.raise_for_status()
        return r.json()

    def download_file(self, download_url: str) -> bytes:
        token = self.get_token()
        if not token:
            raise RuntimeError("Zoom access token not available")
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(download_url, headers=headers, timeout=120, stream=True)
        r.raise_for_status()
        return r.content
