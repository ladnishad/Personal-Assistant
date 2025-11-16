"""Memory database models."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class MemoryType(str, Enum):
    """Memory type enumeration."""

    FACT = "fact"
    PREFERENCE = "preference"
    ROUTINE = "routine"
    RELATIONSHIP = "relationship"
    CONTEXT = "context"
    NOTE = "note"


class Memory(Document):
    """Memory document model for long-term storage."""

    user_id: Indexed(PydanticObjectId)

    # Memory content
    content: str
    memory_type: Indexed(MemoryType)
    category: Optional[str] = None

    # Source tracking
    source_type: Optional[str] = None  # email, task, calendar, manual
    source_id: Optional[str] = None

    # Metadata
    tags: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)

    # Temporal
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    access_count: int = Field(default=0)

    # Embeddings for semantic search
    embedding: List[float] = Field(default_factory=list)
    embedded_at: Optional[datetime] = None

    # Timestamps
    created_at: Indexed(datetime, index_type=-1)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "memories"
        indexes = [
            [("user_id", 1), ("memory_type", 1)],
            [("user_id", 1), ("created_at", -1)],
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "content": "User prefers morning meetings between 9-11 AM",
                "memory_type": "preference",
                "category": "scheduling",
                "tags": ["meetings", "schedule"],
                "confidence": 0.9,
                "importance": 0.8,
            }
        }
