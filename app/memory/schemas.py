"""Memory request/response schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.memory.models import MemoryType


class MemoryCreate(BaseModel):
    """Memory creation request."""

    content: str
    memory_type: MemoryType
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)


class MemoryResponse(BaseModel):
    """Memory response."""

    id: str = Field(..., alias="_id")
    user_id: str
    content: str
    memory_type: MemoryType
    category: Optional[str] = None
    tags: List[str]
    confidence: float
    importance: float
    access_count: int
    created_at: datetime

    class Config:
        populate_by_name = True


class MemoryListResponse(BaseModel):
    """Memory list response."""

    memories: List[MemoryResponse]
    total: int


class MemorySearchRequest(BaseModel):
    """Memory search request."""

    query: str
    limit: int = Field(default=10, ge=1, le=50)
    memory_type: Optional[MemoryType] = None


class MemorySearchResponse(BaseModel):
    """Memory search result."""

    memory: MemoryResponse
    score: float
