"""Task service layer."""

import logging
from datetime import datetime
from typing import List, Optional

from beanie import PydanticObjectId

from app.tasks.models import Task, TaskPriority, TaskStatus
from app.tasks.schemas import TaskCreate, TaskUpdate

logger = logging.getLogger(__name__)


class TaskService:
    """Task service."""

    @staticmethod
    async def create_task(user_id: PydanticObjectId, task_data: TaskCreate) -> Task:
        """Create a new task."""
        task = Task(user_id=user_id, **task_data.model_dump())
        await task.insert()
        logger.info(f"Task created: {task.title} for user {user_id}")
        return task

    @staticmethod
    async def get_task(task_id: str, user_id: PydanticObjectId) -> Task:
        """Get a single task by ID."""
        task = await Task.get(task_id)

        if not task or task.user_id != user_id:
            raise ValueError("Task not found")

        return task

    @staticmethod
    async def update_task(
        task_id: str, user_id: PydanticObjectId, task_data: TaskUpdate
    ) -> Task:
        """Update a task."""
        task = await Task.get(task_id)

        if not task or task.user_id != user_id:
            raise ValueError("Task not found")

        # Update fields
        update_data = task_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        # If status changed to done, set completed_at
        if task_data.status == TaskStatus.DONE and not task.completed_at:
            task.completed_at = datetime.utcnow()

        task.updated_at = datetime.utcnow()
        await task.save()

        logger.info(f"Task updated: {task.title}")
        return task

    @staticmethod
    async def get_user_tasks(
        user_id: PydanticObjectId,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[Task], int]:
        """Get user tasks with filters.

        Tasks are sorted with incomplete (todo) tasks first, then completed (done) tasks,
        with each group sorted by created_at descending (newest first).
        """
        query = {"user_id": user_id}

        if status:
            query["status"] = status

        if priority:
            query["priority"] = priority

        # Get total count
        total = await Task.find(query).count()

        # Get all tasks (before pagination) to sort properly
        all_tasks = await Task.find(query).sort(-Task.created_at).to_list()

        # Sort: incomplete first, then completed, both newest first
        sorted_tasks = sorted(
            all_tasks,
            key=lambda t: (t.status == TaskStatus.DONE, -t.created_at.timestamp()),
        )

        # Apply pagination after sorting
        tasks = sorted_tasks[skip : skip + limit]

        return tasks, total

    @staticmethod
    async def delete_task(task_id: str, user_id: PydanticObjectId) -> bool:
        """Delete a task."""
        task = await Task.get(task_id)

        if not task or task.user_id != user_id:
            raise ValueError("Task not found")

        await task.delete()
        logger.info(f"Task deleted: {task.title}")
        return True
