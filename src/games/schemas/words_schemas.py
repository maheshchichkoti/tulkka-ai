# src/games/schemas/words_schemas.py
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class WordCreate(BaseModel):
    word: str = Field(..., min_length=1, max_length=255)
    translation: Optional[str]
    notes: Optional[str]
    difficulty: Optional[str]

class WordUpdate(BaseModel):
    word: Optional[str]
    translation: Optional[str]
    notes: Optional[str]
    isFavorite: Optional[bool]
    difficulty: Optional[str]

class WordOut(BaseModel):
    id: str
    wordListId: str
    word: str
    translation: Optional[str]
    notes: Optional[str]
    difficulty: Optional[str]
    practiceCount: int
    correctCount: int
    accuracy: int
    isFavorite: bool
    lastPracticed: Optional[datetime]
    createdAt: datetime
    updatedAt: datetime
