# src/games/schemas/sessions_schemas.py
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class StartSessionIn(BaseModel):
    userId: str
    gameType: str
    classId: Optional[str] = None
    referenceId: Optional[str] = None
    itemIds: Optional[List[str]] = None
    mode: Optional[str] = None

class PracticeResultIn(BaseModel):
    itemId: str
    isCorrect: bool
    attempts: int = Field(default=1, ge=1)
    timeSpentMs: int = Field(default=0, ge=0)
    metadata: Optional[dict] = None

class SessionCompleteIn(BaseModel):
    finalScore: Optional[float]
    correctCount: Optional[int] = 0
    incorrectCount: Optional[int] = 0

class SessionOut(BaseModel):
    id: str
    userId: str
    gameType: str
    classId: Optional[str]
    itemIds: Optional[List[str]]
    status: str
    progressCurrent: int
    progressTotal: int
    correctCount: int
    incorrectCount: int
    finalScore: Optional[float]
    metadata: Optional[Any]
    startedAt: datetime
    completedAt: Optional[datetime]
