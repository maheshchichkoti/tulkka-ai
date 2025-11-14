# src/games/schemas/common.py
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime

class Pagination(BaseModel):
    page: int = Field(default=1)
    limit: int = Field(default=20)
    total: int = Field(default=0)

class APIError(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class SuccessResponse(BaseModel):
    status: str = "success"
