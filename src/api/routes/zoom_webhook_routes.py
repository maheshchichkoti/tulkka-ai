"""
Zoom Recording Webhook Routes
Handles incoming webhook requests from n8n for Zoom recording processing
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
import re

from ...db.supabase_client import SupabaseClient
from ...ai.lesson_processor import LessonProcessor
from ...time_utils import utc_now_iso

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/webhooks", tags=["Zoom Webhooks"])

supabase = SupabaseClient()
lesson_processor = LessonProcessor()


class ZoomRecordingWebhookRequest(BaseModel):
    """Request model for Zoom recording webhook from n8n"""
    teacherEmail: str = Field(..., description="Teacher's Zoom email")
    date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$', description="Recording date (YYYY-MM-DD)")
    startTime: str = Field(..., description="Start time (HH:MM)")
    endTime: str = Field(..., description="End time (HH:MM)")
    user_id: str = Field(..., description="Student user ID")
    teacher_id: str = Field(..., description="Teacher ID")
    class_id: str = Field(..., description="Class ID")
    
    # Optional fields from n8n
    meetingId: Optional[str] = None
    meetingTopic: Optional[str] = None
    duration: Optional[int] = None
    recordingUrls: Optional[List[str]] = None
    transcript: Optional[str] = None
    transcriptUrl: Optional[str] = None
    
    @validator('startTime', 'endTime')
    def validate_time_format(cls, v):
        """Validate time format HH:MM"""
        if not re.match(r'^\d{2}:\d{2}$', v):
            raise ValueError('Time must be in HH:MM format (24-hour)')
        hours, minutes = v.split(':')
        if int(hours) > 23 or int(minutes) > 59:
            raise ValueError('Invalid time value')
        return v


class ZoomRecordingResponse(BaseModel):
    """Response model for webhook"""
    status: str
    message: str
    zoom_summary_id: Optional[int] = None
    recordingsProcessed: Optional[int] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: str


@router.post("/zoom-recording-download", response_model=ZoomRecordingResponse)
async def handle_zoom_recording_webhook(
    payload: ZoomRecordingWebhookRequest,
    background_tasks: BackgroundTasks
):
    """
    Webhook endpoint to receive Zoom recording data from n8n
    
    This endpoint receives processed Zoom recordings from n8n workflow and:
    1. Stores recording metadata in Supabase
    2. Processes transcript if available
    3. Generates exercises in background
    
    Returns immediately with success status while processing continues in background.
    """
    try:
        logger.info(f"Received Zoom recording webhook for teacher={payload.teacherEmail}, date={payload.date}")
        
        # Prepare data for Supabase storage
        zoom_summary_data = {
            'meeting_id': payload.meetingId or f"{payload.teacherEmail}_{payload.date}_{payload.startTime}",
            'meeting_topic': payload.meetingTopic or f"Lesson {payload.date}",
            'teacher_email': payload.teacherEmail,
            'meeting_date': payload.date,
            'start_time': payload.startTime,
            'end_time': payload.endTime,
            'duration': payload.duration or 0,
            'user_id': payload.user_id,
            'teacher_id': payload.teacher_id,
            'class_id': payload.class_id,
            'recording_urls': payload.recordingUrls or [],
            'transcript': payload.transcript or '',
            'transcript_url': payload.transcriptUrl or '',
            'status': 'pending_processing' if payload.transcript else 'pending_transcript',
            'created_at': utc_now_iso(),
            'updated_at': utc_now_iso()
        }
        
        # Store in Supabase
        try:
            # Check if recording already exists
            existing = supabase.fetch_zoom_summary(
                user_id=payload.user_id,
                teacher_id=payload.teacher_id,
                class_id=payload.class_id,
                meeting_date=payload.date
            )
            
            if existing:
                logger.info(f"Updating existing Zoom summary ID: {existing.get('id')}")
                zoom_summary_id = existing.get('id')
                supabase.update_zoom_summary(zoom_summary_id, zoom_summary_data)
            else:
                logger.info("Creating new Zoom summary")
                result = supabase.insert_zoom_summary(zoom_summary_data)
                zoom_summary_id = result.get('id') if result else None
        
        except Exception as e:
            logger.error(f"Supabase storage error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to store recording data: {str(e)}"
            )
        
        # If transcript is available, process it in background
        if payload.transcript and zoom_summary_id:
            logger.info(f"Scheduling background processing for zoom_summary_id={zoom_summary_id}")
            background_tasks.add_task(
                process_zoom_transcript_background,
                zoom_summary_id=zoom_summary_id,
                transcript=payload.transcript,
                user_id=payload.user_id,
                teacher_id=payload.teacher_id,
                class_id=payload.class_id,
                lesson_number=1  # Default, can be enhanced
            )
        
        # Return success response
        return ZoomRecordingResponse(
            status="success",
            message="Zoom recording received and stored successfully",
            zoom_summary_id=zoom_summary_id,
            recordingsProcessed=1,
            data={
                "meetingId": payload.meetingId,
                "teacherEmail": payload.teacherEmail,
                "date": payload.date,
                "userContext": {
                    "userId": payload.user_id,
                    "teacherId": payload.teacher_id,
                    "classId": payload.class_id
                },
                "processingStatus": "background" if payload.transcript else "awaiting_transcript"
            },
            timestamp=utc_now_iso()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Webhook processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": str(e),
                "errorType": "WebhookProcessingError",
                "context": {
                    "teacherEmail": payload.teacherEmail,
                    "date": payload.date,
                    "timestamp": utc_now_iso()
                }
            }
        )


async def process_zoom_transcript_background(
    zoom_summary_id: int,
    transcript: str,
    user_id: str,
    teacher_id: str,
    class_id: str,
    lesson_number: int
):
    """
    Background task to process Zoom transcript and generate exercises
    """
    try:
        logger.info(f"Processing transcript for zoom_summary_id={zoom_summary_id}")
        
        # Process the transcript
        result = lesson_processor.process_lesson(transcript, lesson_number)
        
        # Store exercises in Supabase
        exercises_payload = {
            'zoom_summary_id': zoom_summary_id,
            'user_id': user_id,
            'teacher_id': teacher_id,
            'class_id': class_id,
            'lesson_number': lesson_number,
            'exercises': result,
            'generated_at': utc_now_iso(),
            'status': 'completed'
        }
        
        supabase.insert_lesson_exercises(exercises_payload)
        
        # Update zoom_summary status
        supabase.update_zoom_summary(zoom_summary_id, {
            'status': 'completed',
            'updated_at': utc_now_iso()
        })
        
        logger.info(f"Successfully processed zoom_summary_id={zoom_summary_id}")
        
    except Exception as e:
        logger.exception(f"Background processing failed for zoom_summary_id={zoom_summary_id}: {e}")
        
        # Update status to failed
        try:
            supabase.update_zoom_summary(zoom_summary_id, {
                'status': 'failed',
                'error_message': str(e),
                'updated_at': utc_now_iso()
            })
        except:
            pass


@router.get("/zoom-recording-status/{zoom_summary_id}")
async def get_zoom_recording_status(zoom_summary_id: int):
    """
    Check the processing status of a Zoom recording
    """
    try:
        summary = supabase.get_zoom_summary_by_id(zoom_summary_id)
        
        if not summary:
            raise HTTPException(status_code=404, detail="Recording not found")
        
        return {
            "zoom_summary_id": zoom_summary_id,
            "status": summary.get('status'),
            "meeting_topic": summary.get('meeting_topic'),
            "meeting_date": summary.get('meeting_date'),
            "created_at": summary.get('created_at'),
            "updated_at": summary.get('updated_at'),
            "error_message": summary.get('error_message')
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
