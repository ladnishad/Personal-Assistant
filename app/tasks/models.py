"""Task database models."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class TaskStatus(str, Enum):
    """Task status enumeration."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(Document):
    """Task document model."""

    user_id: Indexed(PydanticObjectId)

    # Task details
    title: str
    description: Optional[str] = None
    status: TaskStatus = Field(default=TaskStatus.TODO)  # Cannot use Indexed() with Enums
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)

    # Dates
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Source tracking
    source_type: Optional[str] = None  # email, calendar, manual
    source_id: Optional[str] = None  # ID of source document

    # Tags and categories
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None

    # Reminders
    reminder_at: Optional[datetime] = None
    reminder_sent: bool = Field(default=False)

    # Rich content
    content: Optional[str] = None  # Markdown/rich text content for task details

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Embeddings
    embedding: Optional[List[float]] = None
    embedded_at: Optional[datetime] = None

    class Settings:
        name = "tasks"
        indexes = [
            [("user_id", 1), ("status", 1)],
            [("user_id", 1), ("due_date", 1)],
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Review quarterly report",
                "description": "Review Q1 financial report before meeting",
                "status": "todo",
                "priority": "high",
                "due_date": "2024-01-20T17:00:00",
                "tags": ["work", "finance"],
            }
        }
