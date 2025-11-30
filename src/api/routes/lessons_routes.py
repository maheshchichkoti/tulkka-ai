"""Lesson processing API routes.

Provides endpoints for:
- Processing transcripts into exercises
- Triggering async lesson processing from Zoom recordings
- Checking processing status
- Retrieving generated exercises
"""

from __future__ import annotations
import logging
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from ...ai.lesson_processor import LessonProcessor
from ...db.supabase_client import SupabaseClient, SupabaseClientError
from ...time_utils import utc_now_iso

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["Lesson Processing"])

# Initialize services (lazy initialization would be better for testing)
lesson_processor = LessonProcessor()
supabase = SupabaseClient()

class TranscriptInput(BaseModel):
    """Input model for transcript processing."""
    transcript: str = Field(..., min_length=10, max_length=500000, description="Transcript text")
    lesson_number: int = Field(1, ge=1, le=1000, description="Lesson number")
    user_id: Optional[str] = Field(None, max_length=100)
    teacher_id: Optional[str] = Field(None, max_length=100)
    class_id: Optional[str] = Field(None, max_length=100)
    
    @field_validator('transcript')
    @classmethod
    def validate_transcript(cls, v: str) -> str:
        """Ensure transcript has meaningful content."""
        stripped = v.strip()
        if len(stripped) < 10:
            raise ValueError('Transcript must contain at least 10 characters')
        return stripped

class ZoomLessonInput(BaseModel):
    """Input for triggering lesson processing from backend"""
    teacherEmail: str = Field(..., description="Teacher's Zoom email")
    date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$', description="Class date (YYYY-MM-DD)")
    startTime: str = Field(..., description="Start time (HH:MM)")
    endTime: str = Field(..., description="End time (HH:MM)")
    user_id: str = Field(..., description="Student/user ID from MySQL")
    teacher_id: str = Field(..., description="Teacher ID from MySQL")
    class_id: str = Field(..., description="Class ID from MySQL")
    lesson_number: int = Field(1, ge=1, description="Lesson number")
    meetingId: Optional[str] = Field(None, description="Zoom meeting ID if known")
    meetingTopic: Optional[str] = Field(None, description="Meeting topic")

@router.post("/process")
def process_transcript(payload: TranscriptInput) -> Dict[str, Any]:
    """
    Process a single transcript and generate exercises.
    
    Returns generated exercises including flashcards, spelling, fill-blank,
    sentence builder, grammar challenge, and advanced cloze exercises.
    """
    try:
        result = lesson_processor.process_lesson(
            payload.transcript,
            payload.lesson_number
        )
        
        # Store in Supabase if all IDs provided
        stored = False
        if payload.user_id and payload.teacher_id and payload.class_id:
            try:
                exercises_payload = {
                    'user_id': payload.user_id,
                    'teacher_id': payload.teacher_id,
                    'class_id': payload.class_id,
                    'lesson_number': payload.lesson_number,
                    'exercises': result,
                    'generated_at': utc_now_iso(),
                    'status': 'pending_approval'
                }
                supabase.insert_lesson_exercises(exercises_payload)
                stored = True
            except SupabaseClientError as e:
                logger.warning("Failed to store exercises in Supabase: %s", e)
            except Exception as e:
                logger.warning("Unexpected error storing exercises: %s", e)
        
        return {
            'success': True,
            'lesson_number': payload.lesson_number,
            'exercises': result,
            'metadata': result.get('metadata', {}),
            'stored': stored
        }
        
    except ValueError as e:
        logger.warning("Validation error in process_transcript: %s", e)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Error processing transcript")
        raise HTTPException(status_code=500, detail="Failed to process transcript")

@router.post("/trigger-lesson-processing")
def trigger_lesson_processing(payload: ZoomLessonInput):
    """
    Main endpoint for backend to trigger lesson processing
    
    Flow:
    1. Create pending row in Supabase zoom_summaries
    2. Background worker will:
       - Fetch Zoom recording
       - Transcribe (Zoom native or AssemblyAI)
       - Generate exercises
       - Store in lesson_exercises table
    
    Returns immediately with tracking ID
    """
    try:
        # Check if already processed (match by class_id, date, and time to allow multiple lessons per day)
        existing = supabase.fetch_zoom_summary(
            class_id=payload.class_id,
            meeting_date=payload.date,
            start_time=payload.startTime
        )
        
        if existing:
            status = existing.get('status')
            status_messages = {
                'pending': 'Queued for processing',
                'processing': 'Currently being processed by worker',
                'awaiting_exercises': 'Transcript ready, exercises pending',
                'completed': 'Fully processed with exercises',
                'failed': 'Processing failed - check error details'
            }
            return {
                'success': True,
                'message': f'Lesson already exists: {status_messages.get(status, status)}',
                'zoom_summary_id': existing.get('id'),
                'status': status,
                'transcript_available': bool(existing.get('transcript')),
                'exercises_generated': status == 'completed',
                'check_status_url': f'/v1/lesson-status/{existing.get("id")}'
            }
        
        # Create pending row in Supabase
        zoom_summary_row = {
            'user_id': payload.user_id,
            'teacher_id': payload.teacher_id,
            'class_id': payload.class_id,
            'teacher_email': payload.teacherEmail,
            'meeting_date': payload.date,
            'start_time': payload.startTime,
            'end_time': payload.endTime,
            'meeting_topic': payload.meetingTopic or f"Class {payload.class_id}",
            'lesson_number': payload.lesson_number,
            'status': 'pending',
            'processing_attempts': 0,
            'created_at': utc_now_iso()
        }
        
        # Add optional fields only if provided
        if payload.meetingId:
            zoom_summary_row['meeting_id'] = payload.meetingId
        
        result = supabase.insert_zoom_summary(zoom_summary_row)
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create Supabase record")
        
        zoom_summary_id = result.get('id')
        
        logger.info(f"✅ Created pending zoom summary {zoom_summary_id} for class {payload.class_id} on {payload.date} at {payload.startTime}")
        
        return {
            'success': True,
            'message': 'Lesson processing queued successfully',
            'zoom_summary_id': zoom_summary_id,
            'status': 'pending',
            'class_id': payload.class_id,
            'lesson_number': payload.lesson_number,
            'meeting_date': payload.date,
            'estimated_processing_time': '1-2 minutes',
            'next_steps': [
                'Worker will fetch Zoom recording',
                'Transcribe audio (if needed)',
                'Generate exercises with AI',
                'Store in lesson_exercises table'
            ],
            'check_status_url': f'/v1/lesson-status/{zoom_summary_id}',
            'check_exercises_url': f'/v1/exercises?class_id={payload.class_id}'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error triggering lesson processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lesson-status/{zoom_summary_id}")
def get_lesson_status(zoom_summary_id: int):
    """
    Check processing status of a lesson
    
    Statuses:
    - pending: Waiting for worker to pick up
    - processing: Worker is currently processing
    - completed: Exercises generated and stored
    - failed: Processing failed (check last_error)
    """
    try:
        summary = supabase.get_zoom_summary_by_id(zoom_summary_id)
        
        if not summary:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        # Check if exercises were generated
        exercises = None
        if summary.get('status') == 'completed':
            try:
                resp = supabase.client.table('lesson_exercises').select('*').eq(
                    'zoom_summary_id', zoom_summary_id
                ).execute()
                exercises_data = getattr(resp, 'data', []) or []
                if exercises_data:
                    exercises = exercises_data[0]
            except Exception:
                pass
        
        return {
            'success': True,
            'zoom_summary_id': zoom_summary_id,
            'status': summary.get('status'),
            'class_id': summary.get('class_id'),
            'user_id': summary.get('user_id'),
            'teacher_id': summary.get('teacher_id'),
            'transcript_available': bool(summary.get('transcript')),
            'transcript_length': summary.get('transcript_length', 0),
            'transcription_source': summary.get('transcript_source'),
            'processing_attempts': summary.get('processing_attempts', 0),
            'last_error': summary.get('last_error'),
            'created_at': summary.get('created_at'),
            'processed_at': summary.get('processed_at'),
            'exercises_generated': bool(exercises),
            'exercises_id': exercises.get('id') if exercises else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching lesson status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/exercises")
def get_exercises(class_id: str, user_id: Optional[str] = None):
    """Get generated exercises for a class"""
    try:
        if not supabase.client:
            raise HTTPException(status_code=503, detail="Supabase not available")
        
        query = supabase.client.table('lesson_exercises').select('*').eq('class_id', class_id)
        if user_id:
            query = query.eq('user_id', user_id)
        
        resp = query.order('generated_at', desc=True).execute()
        exercises = getattr(resp, 'data', []) or []
        
        return {
            'success': True,
            'count': len(exercises),
            'exercises': exercises
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching exercises: {e}")
        raise HTTPException(status_code=500, detail=str(e))
