# src/workers/class_monitor.py
"""
Production-ready class monitor that watches MySQL classes table
and automatically triggers n8n when lessons end.
"""
import logging
import time
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests

from ..config import settings

logger = logging.getLogger(__name__)

# Configuration
POLL_INTERVAL = int(settings.WORKER_POLL_INTERVAL_SECONDS)  # Use same interval as worker
N8N_WEBHOOK_URL = settings.N8N_WEBHOOK_URL
BATCH_SIZE = 50  # Process up to 50 ended classes per poll


async def get_ended_classes() -> List[Dict[str, Any]]:
    """
    Fetch classes that have ended but haven't triggered AI processing yet.
    Returns list of class rows with teacher email joined.
    """
    from ..db.mysql_pool import execute_query
    
    query = """
        SELECT 
            c.id AS class_id,
            c.student_id,
            c.teacher_id,
            c.meeting_start,
            c.meeting_end,
            c.zoom_id,
            c.status,
            u.email AS teacher_email,
            c.ai_triggered
        FROM classes c
        LEFT JOIN users u ON u.id = c.teacher_id
        WHERE c.status = 'ended'
          AND c.meeting_end IS NOT NULL
          AND (c.ai_triggered IS NULL OR c.ai_triggered = 0)
        ORDER BY c.meeting_end ASC
        LIMIT %s
    """
    
    try:
        rows = await execute_query(query, (BATCH_SIZE,), fetchall=True)
        return rows or []
    except Exception as e:
        logger.exception(f"Failed to fetch ended classes: {e}")
        return []


async def mark_class_triggered(class_id: int) -> bool:
    """Mark a class as AI-triggered to prevent duplicate processing."""
    from ..db.mysql_pool import execute_query
    
    query = """
        UPDATE classes 
        SET ai_triggered = 1,
            updated_at = NOW()
        WHERE id = %s
    """
    
    try:
        await execute_query(query, (class_id,))
        return True
    except Exception as e:
        logger.exception(f"Failed to mark class {class_id} as triggered: {e}")
        return False


def trigger_n8n_for_class(class_row: Dict[str, Any]) -> bool:
    """
    Call FastAPI /v1/trigger-n8n endpoint for a single class.
    Returns True if successful, False otherwise.
    """
    if not N8N_WEBHOOK_URL:
        logger.warning("N8N_WEBHOOK_URL not configured, skipping trigger")
        return False
    
    try:
        # Extract data from class row
        class_id = class_row.get('class_id')
        student_id = class_row.get('student_id')
        teacher_id = class_row.get('teacher_id')
        meeting_start = class_row.get('meeting_start')
        meeting_end = class_row.get('meeting_end')
        teacher_email = class_row.get('teacher_email')
        
        # Validate required fields
        if not all([class_id, student_id, teacher_id, meeting_start, meeting_end]):
            logger.warning(f"Class {class_id} missing required fields, skipping")
            return False
        
        # Format datetime fields
        if isinstance(meeting_start, datetime):
            date = meeting_start.strftime('%Y-%m-%d')
            start_time = meeting_start.strftime('%H:%M')
        else:
            date = str(meeting_start)[:10]
            start_time = str(meeting_start)[11:16]
        
        if isinstance(meeting_end, datetime):
            end_time = meeting_end.strftime('%H:%M')
        else:
            end_time = str(meeting_end)[11:16]
        
        # Build payload for n8n
        payload = {
            'user_id': str(student_id),
            'teacher_id': str(teacher_id),
            'class_id': str(class_id),
            'date': date,
            'start_time': start_time,
            'end_time': end_time,
            'teacher_email': teacher_email or 'unknown@example.com'
        }
        
        logger.info(f"Triggering n8n for class {class_id}: {date} {start_time}-{end_time}")
        
        # Call n8n webhook directly
        response = requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code in [200, 201, 202]:
            logger.info(f"Successfully triggered n8n for class {class_id}")
            return True
        else:
            logger.error(f"n8n returned status {response.status_code} for class {class_id}: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling n8n for class {class_id}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error calling n8n for class {class_id}: {e}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error triggering n8n for class {class_id}: {e}")
        return False


async def process_ended_classes():
    """
    Main processing loop: fetch ended classes, trigger n8n, mark as processed.
    """
    try:
        # Fetch ended classes
        ended_classes = await get_ended_classes()
        
        if not ended_classes:
            logger.debug("No ended classes to process")
            return
        
        logger.info(f"Found {len(ended_classes)} ended classes to process")
        
        # Process each class
        for class_row in ended_classes:
            class_id = class_row.get('class_id')
            
            try:
                # Trigger n8n
                success = trigger_n8n_for_class(class_row)
                
                if success:
                    # Mark as triggered to prevent reprocessing
                    await mark_class_triggered(class_id)
                    logger.info(f"Class {class_id} processed and marked as triggered")
                else:
                    logger.warning(f"Failed to trigger n8n for class {class_id}, will retry next poll")
                    
            except Exception as e:
                logger.exception(f"Error processing class {class_id}: {e}")
                continue
        
        logger.info(f"Finished processing {len(ended_classes)} classes")
        
    except Exception as e:
        logger.exception(f"Error in process_ended_classes: {e}")


async def run_forever():
    """
    Main event loop: continuously monitor classes table and trigger n8n.
    """
    from ..db.mysql_pool import AsyncMySQLPool
    
    logger.info(f"Class monitor started. Poll interval: {POLL_INTERVAL}s")
    logger.info(f"N8N webhook URL: {N8N_WEBHOOK_URL or 'NOT CONFIGURED'}")
    
    # Initialize MySQL pool
    try:
        await AsyncMySQLPool.init_pool()
        logger.info("MySQL pool initialized for class monitor")
    except Exception as e:
        logger.exception(f"Failed to initialize MySQL pool: {e}")
        logger.error("Class monitor cannot run without MySQL connection")
        return
    
    if not N8N_WEBHOOK_URL:
        logger.error("N8N_WEBHOOK_URL not configured. Class monitor will not trigger n8n.")
        logger.error("Set N8N_WEBHOOK_URL in .env to enable automatic lesson processing.")
    
    # Main loop
    while True:
        try:
            await process_ended_classes()
            await asyncio.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("Class monitor interrupted by user, shutting down...")
            break
        except Exception as e:
            logger.exception(f"Unexpected error in class monitor loop: {e}")
            await asyncio.sleep(min(POLL_INTERVAL, 60))
    
    # Cleanup
    try:
        await AsyncMySQLPool.close_pool()
        logger.info("MySQL pool closed")
    except Exception as e:
        logger.exception(f"Error closing MySQL pool: {e}")


def main():
    """Entry point for running class monitor as standalone service."""
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
