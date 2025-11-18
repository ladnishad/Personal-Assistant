"""Task request/response schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_serializer

from app.tasks.models import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    """Task creation request."""

    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None


class TaskUpdate(BaseModel):
    """Task update request."""

    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    content: Optional[str] = None


class TaskResponse(BaseModel):
    """Task response."""

    id: str = Field(..., serialization_alias="_id")
    user_id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    reminder_at: Optional[datetime] = None
    reminder_sent: bool
    tags: List[str]
    category: Optional[str] = None
    content: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer('created_at', 'updated_at', 'due_date', 'completed_at', 'reminder_at')
    def serialize_datetime(self, dt: Optional[datetime], _info):
        """Serialize datetime to ISO8601 format without microseconds."""
        if dt is None:
            return None
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    model_config = {
        "populate_by_name": True
    }


class TaskListResponse(BaseModel):
    """Task list response."""

    tasks: List[TaskResponse]
    total: int
