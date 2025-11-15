"""Lesson processing API routes"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
from ...ai.lesson_processor import LessonProcessor
from ...db.supabase_client import SupabaseClient
from ...time_utils import utc_now_iso
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["Lesson Processing"])

lesson_processor = LessonProcessor()
supabase = SupabaseClient()

class TranscriptInput(BaseModel):
    transcript: str = Field(..., min_length=10)
    lesson_number: int = Field(1, ge=1)
    user_id: Optional[str] = None
    teacher_id: Optional[str] = None
    class_id: Optional[str] = None

class ZoomLessonInput(BaseModel):
    user_id: str
    teacher_id: str
    class_id: str
    date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    lesson_number: int = Field(1, ge=1)
    meeting_id: Optional[str] = None
    start_time: Optional[str] = None  # Format: "HH:MM"
    end_time: Optional[str] = None    # Format: "HH:MM"
    teacher_email: Optional[str] = None

@router.post("/process")
def process_transcript(payload: TranscriptInput):
    """Process a single transcript and generate exercises"""
    try:
        result = lesson_processor.process_lesson(
            payload.transcript,
            payload.lesson_number
        )
        
        # Store in Supabase if IDs provided
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
            except Exception as e:
                logger.warning(f"Failed to store exercises: {e}")
        
        return {
            'success': True,
            'lesson_number': payload.lesson_number,
            'exercises': result,
            'metadata': result.get('metadata', {})
        }
    except Exception as e:
        logger.exception(f"Error processing transcript: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-zoom-lesson")
def process_zoom_lesson(payload: ZoomLessonInput, background_tasks: BackgroundTasks):
    """Fetch transcript from Zoom/Supabase and process"""
    try:
        # Fetch transcript from Supabase
        summary = supabase.fetch_zoom_summary(
            user_id=payload.user_id,
            teacher_id=payload.teacher_id,
            class_id=payload.class_id,
            meeting_date=payload.date
        )
        
        if not summary:
            raise HTTPException(status_code=404, detail="Zoom transcript not found")
        
        transcript = summary.get('transcript')
        if not transcript:
            raise HTTPException(status_code=400, detail="Transcript is empty")
        
        # Process in background
        def process_task():
            try:
                result = lesson_processor.process_lesson(transcript, payload.lesson_number)
                
                # Store exercises
                exercises_payload = {
                    'zoom_summary_id': summary.get('id'),
                    'user_id': payload.user_id,
                    'teacher_id': payload.teacher_id,
                    'class_id': payload.class_id,
                    'lesson_number': payload.lesson_number,
                    'exercises': result,
                    'generated_at': utc_now_iso(),
                    'status': 'pending_approval'
                }
                supabase.insert_lesson_exercises(exercises_payload)
                logger.info(f"Processed zoom lesson for {payload.user_id}/{payload.class_id}/{payload.date}")
            except Exception as e:
                logger.exception(f"Background processing failed: {e}")
        
        background_tasks.add_task(process_task)
        
        return {
            'success': True,
            'message': 'Processing started',
            'zoom_summary_id': summary.get('id'),
            'lesson_number': payload.lesson_number
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing zoom lesson: {e}")
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
