from typing import Optional, Dict, Any, List
from supabase import create_client, Client
import logging
from ..config import settings

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Light wrapper around supabase client for zoom_summaries and lesson_exercises."""

    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_KEY
        self.client: Optional[Client] = None
        if not self.url or not self.key:
            logger.warning("Supabase credentials not found. Supabase client disabled.")
            return
        try:
            self.client = create_client(self.url, self.key)
            logger.info("Supabase client initialized.")
        except Exception as e:
            logger.exception("Failed to initialize Supabase client: %s", e)
            self.client = None

    def health_check(self) -> bool:
        if not self.client:
            return False
        try:
            resp = self.client.table("zoom_summaries").select("id").limit(1).execute()
            return bool(getattr(resp, "data", None))
        except Exception:
            logger.exception("Supabase health check failed.")
            return False

    # ------------------------------------------------------------------
    # Insert / Fetch / Update
    # ------------------------------------------------------------------
    def insert_zoom_summary(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        resp = self.client.table("zoom_summaries").insert(row).execute()
        return (getattr(resp, "data", []) or [None])[0]

    def fetch_zoom_summary(self, **filters) -> Optional[Dict[str, Any]]:
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        query = self.client.table("zoom_summaries").select("*")
        for k, v in filters.items():
            query = query.eq(k, v)
        resp = query.order("created_at", desc=True).limit(1).execute()
        return (getattr(resp, "data", []) or [None])[0]

    def update_zoom_summary(self, row_id: Any, payload: Dict[str, Any]) -> bool:
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        resp = self.client.table("zoom_summaries").update(payload).eq("id", row_id).execute()
        return bool(getattr(resp, "data", None))

    def insert_lesson_exercises(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        resp = self.client.table("lesson_exercises").insert(payload).execute()
        return (getattr(resp, "data", []) or [None])[0]

    # ------------------------------------------------------------------
    # Task Fetching – PENDING
    # ------------------------------------------------------------------
    def find_pending_summaries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return pending summaries eligible for processing."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        resp = (
            self.client.table("zoom_summaries")
            .select("*")
            .eq("status", "pending")
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return getattr(resp, "data", []) or []

    def get_zoom_summary_by_id(self, zoom_summary_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific zoom summary by ID."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        resp = (
            self.client.table("zoom_summaries")
            .select("*")
            .eq("id", zoom_summary_id)
            .limit(1)
            .execute()
        )
        return (getattr(resp, "data", []) or [None])[0]

    # ------------------------------------------------------------------
    # 🔥 NEW: Reclaim Stale Processing Tasks
    # ------------------------------------------------------------------
    def find_processing_older_than(self, cutoff_unix_timestamp: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Returns tasks that:
          - are still "processing"
          - AND processing_started_at < cutoff timestamp
        Used to recover tasks if the worker crashed and left jobs stuck.
        """

        if not self.client:
            raise RuntimeError("Supabase client not initialized")

        try:
            # Convert unix timestamp to ISO8601 because Supabase stores timestamps as text
            cutoff_iso = (
                # Convert int UNIX → datetime → isoformat
                __import__("datetime").datetime.utcfromtimestamp(cutoff_unix_timestamp).isoformat()
            )

            logger.info(
                "Looking for stale processing summaries older than %s (limit=%s)",
                cutoff_iso,
                limit,
            )

            resp = (
                self.client.table("zoom_summaries")
                .select("*")
                .eq("status", "processing")
                .lt("processing_started_at", cutoff_iso)
                .order("processing_started_at", desc=False)
                .limit(limit)
                .execute()
            )

            return getattr(resp, "data", []) or []

        except Exception:
            logger.exception("Failed fetching stale processing rows")
            return []
