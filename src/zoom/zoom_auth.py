# src/zoom/zoom_auth.py
import base64
import logging
from typing import Optional, Dict, Any
import requests
from ..config import settings
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ZoomTokenManager:
    """Handles Zoom OAuth token lifecycle (refresh)."""

    def __init__(self):
        self.client_id = settings.ZOOM_CLIENT_ID
        self.client_secret = settings.ZOOM_CLIENT_SECRET
        self.access_token = settings.ZOOM_ACCESS_TOKEN
        self.refresh_token = settings.ZOOM_REFRESH_TOKEN
        self.expires_at = None  # datetime or None

    def _encode_credentials(self) -> str:
        creds = f"{self.client_id}:{self.client_secret}"
        return base64.b64encode(creds.encode()).decode()

    def is_valid(self) -> bool:
        from datetime import datetime
        if self.access_token and self.expires_at and datetime.utcnow() < self.expires_at:
            return True
        return False

    def load_from_env(self):
        # nothing here; env loaded by config
        pass

    def refresh(self) -> Optional[str]:
        """Refresh using refresh token. Returns access token or None."""
        if not self.refresh_token or not self.client_id or not self.client_secret:
            logger.warning("Zoom refresh credentials missing.")
            return self.access_token

        token_url = "https://zoom.us/oauth/token"
        headers = {
            "Authorization": f"Basic {self._encode_credentials()}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "refresh_token", "refresh_token": self.refresh_token}
        try:
            r = requests.post(token_url, headers=headers, data=data, timeout=15)
            r.raise_for_status()
            payload = r.json()
            self.access_token = payload.get("access_token", self.access_token)
            self.refresh_token = payload.get("refresh_token", self.refresh_token)
            expires_in = payload.get("expires_in", 3600)
            self.expires_at = datetime.utcnow() + timedelta(seconds=max(60, expires_in - 120))
            logger.info("Zoom token refreshed, expires in %ss", expires_in)
            return self.access_token
        except Exception as e:
            logger.exception("Zoom token refresh failed: %s", e)
            return self.access_token
