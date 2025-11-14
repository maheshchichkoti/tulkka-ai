# src/games/schemas/wordlists_schemas.py
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class WordListBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    classId: Optional[str] = None

class WordListCreate(WordListBase):
    pass

class WordListUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    isFavorite: Optional[bool]

class WordListOut(BaseModel):
    id: str
    userId: str
    classId: Optional[str]
    name: str
    description: Optional[str]
    wordCount: int
    isFavorite: bool
    createdAt: datetime
    updatedAt: datetime

class WordListPage(BaseModel):
    data: List[WordListOut]
    pagination: dict
