"""Task API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.tasks.models import TaskPriority, TaskStatus
from app.tasks.schemas import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate
from app.tasks.service import TaskService

router = APIRouter()


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate, current_user: User = Depends(get_current_active_user)
):
    """Create a new task."""
    task = await TaskService.create_task(current_user.id, task_data)
    return TaskResponse(
        id=str(task.id),
        user_id=str(task.user_id),
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        completed_at=task.completed_at,
        reminder_at=task.reminder_at,
        reminder_sent=task.reminder_sent,
        tags=task.tags,
        category=task.category,
        content=task.content,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[TaskStatus] = Query(None),
    priority: Optional[TaskPriority] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
):
    """List user tasks."""
    skip = (page - 1) * page_size

    tasks, total = await TaskService.get_user_tasks(
        user_id=current_user.id,
        status=status,
        priority=priority,
        skip=skip,
        limit=page_size,
    )

    task_responses = [
        TaskResponse(
            id=str(t.id),
            user_id=str(t.user_id),
            title=t.title,
            description=t.description,
            status=t.status,
            priority=t.priority,
            due_date=t.due_date,
            completed_at=t.completed_at,
            reminder_at=t.reminder_at,
            reminder_sent=t.reminder_sent,
            tags=t.tags,
            category=t.category,
            content=t.content,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in tasks
    ]

    return TaskListResponse(tasks=task_responses, total=total)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str, current_user: User = Depends(get_current_active_user)
):
    """Get a single task by ID."""
    try:
        task = await TaskService.get_task(task_id, current_user.id)
        return TaskResponse(
            id=str(task.id),
            user_id=str(task.user_id),
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            due_date=task.due_date,
            completed_at=task.completed_at,
            reminder_at=task.reminder_at,
            reminder_sent=task.reminder_sent,
            tags=task.tags,
            category=task.category,
            content=task.content,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
):
    """Update a task."""
    try:
        task = await TaskService.update_task(task_id, current_user.id, task_data)
        return TaskResponse(
            id=str(task.id),
            user_id=str(task.user_id),
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            due_date=task.due_date,
            completed_at=task.completed_at,
            reminder_at=task.reminder_at,
            reminder_sent=task.reminder_sent,
            tags=task.tags,
            category=task.category,
            content=task.content,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str, current_user: User = Depends(get_current_active_user)
):
    """Delete a task."""
    try:
        await TaskService.delete_task(task_id, current_user.id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
