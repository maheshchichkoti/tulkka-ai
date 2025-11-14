from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class StartSessionRequest(BaseModel):
    wordListId: str = Field(..., min_length=1)
    selectedWordIds: Optional[List[str]] = None

class FlashcardWord(BaseModel):
    id: str
    word: str
    translation: str
    notes: Optional[str] = ""
    isFavorite: bool
    practiceCount: int
    correctCount: int
    accuracy: int
    lastPracticed: Optional[datetime]
    createdAt: datetime
    updatedAt: datetime

class FlashcardProgress(BaseModel):
    current: int
    total: int
    correct: int
    incorrect: int

class FlashcardSession(BaseModel):
    id: str
    wordListId: str
    words: List[FlashcardWord]
    progress: FlashcardProgress
    startedAt: datetime
    completedAt: Optional[datetime]

class PracticeResultRequest(BaseModel):
    wordId: str
    isCorrect: bool
    timeSpent: int = Field(..., ge=0)
    attempts: int = Field(..., ge=1)

class CompleteSessionRequest(BaseModel):
    progress: Optional[FlashcardProgress] = None

class OkResponse(BaseModel):
    ok: bool = True
