"""Agent tools for LLM function calling."""

import logging
from datetime import datetime
from typing import Any, Dict, List

from beanie import PydanticObjectId

from app.emails.service import EmailService
from app.memory.service import MemoryService
from app.tasks.models import TaskPriority, TaskStatus
from app.tasks.schemas import TaskCreate
from app.tasks.service import TaskService

logger = logging.getLogger(__name__)


class AgentTools:
    """Collection of tools available to the AI agent."""

    @staticmethod
    async def search_emails(
        user_id: PydanticObjectId, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search user emails."""
        try:
            emails, _ = await EmailService.get_user_emails(
                user_id=user_id, search=query, limit=limit
            )

            return [
                {
                    "from": e.from_email,
                    "subject": e.subject,
                    "snippet": e.snippet,
                    "received_at": e.received_at.isoformat(),
                }
                for e in emails
            ]
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []

    @staticmethod
    async def create_task(
        user_id: PydanticObjectId,
        title: str,
        description: str = None,
        due_date: str = None,
        priority: str = "medium",
    ) -> Dict[str, Any]:
        """Create a new task."""
        try:
            # Parse priority
            task_priority = TaskPriority(priority.lower())

            # Parse due date
            due_datetime = None
            if due_date:
                due_datetime = datetime.fromisoformat(due_date)

            # Create task
            task_data = TaskCreate(
                title=title,
                description=description,
                due_date=due_datetime,
                priority=task_priority,
            )

            task = await TaskService.create_task(user_id, task_data)

            return {
                "id": str(task.id),
                "title": task.title,
                "status": task.status.value,
                "priority": task.priority.value,
                "created": True,
            }
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return {"error": str(e), "created": False}

    @staticmethod
    async def get_tasks(
        user_id: PydanticObjectId, status: str = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get user tasks."""
        try:
            task_status = TaskStatus(status.lower()) if status else None

            tasks, _ = await TaskService.get_user_tasks(
                user_id=user_id, status=task_status, limit=limit
            )

            return [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "status": t.status.value,
                    "priority": t.priority.value,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                }
                for t in tasks
            ]
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            return []

    @staticmethod
    async def search_memory(
        user_id: PydanticObjectId, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search long-term memory."""
        try:
            results = await MemoryService.semantic_search(
                user_id=user_id, query=query, limit=limit
            )

            return [
                {
                    "content": m.content,
                    "type": m.memory_type.value,
                    "score": score,
                    "importance": m.importance,
                }
                for m, score in results
            ]
        except Exception as e:
            logger.error(f"Error searching memory: {e}")
            return []

    @staticmethod
    def get_tool_definitions() -> List[Dict[str, Any]]:
        """Get OpenAI function calling tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_emails",
                    "description": "Search user's emails by query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for emails",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 5,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_task",
                    "description": "Create a new task or reminder",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Task title"},
                            "description": {
                                "type": "string",
                                "description": "Task description",
                            },
                            "due_date": {
                                "type": "string",
                                "description": "Due date in ISO format",
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "urgent"],
                                "default": "medium",
                            },
                        },
                        "required": ["title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_tasks",
                    "description": "Get user's tasks",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "enum": ["todo", "in_progress", "done", "cancelled"],
                                "description": "Filter by task status",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 10,
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_memory",
                    "description": "Search long-term memory for relevant context",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for memory",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 5,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
        ]
