"""Agent tools for LLM function calling."""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List

from beanie import PydanticObjectId

from app.emails.service import EmailService
from app.memory.models import MemoryType
from app.memory.schemas import MemoryCreate
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
    async def save_memory(
        user_id: PydanticObjectId,
        content: str,
        memory_type: str = "fact",
        category: str = None,
        importance: float = 0.7,
    ) -> Dict[str, Any]:
        """Save information to long-term memory.

        Use this tool whenever you learn new information about the user, such as:
        - Personal information (names of family, friends, pets)
        - Preferences (likes, dislikes, habits)
        - Routines (daily patterns, schedules)
        - Relationships (family members, colleagues, friends)
        - Important facts (allergies, dietary restrictions, etc.)
        """
        try:
            # Validate memory type
            try:
                mem_type = MemoryType(memory_type.lower())
            except ValueError:
                mem_type = MemoryType.FACT

            # Create memory
            memory_data = MemoryCreate(
                content=content,
                memory_type=mem_type,
                category=category,
                importance=min(max(importance, 0.0), 1.0),  # Clamp between 0 and 1
            )

            memory = await MemoryService.create_memory(user_id, memory_data)

            logger.info(f"Memory saved for user {user_id}: {content[:50]}...")

            return {
                "id": str(memory.id),
                "content": memory.content,
                "type": memory.memory_type.value,
                "saved": True,
            }
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
            return {"error": str(e), "saved": False}

    @staticmethod
    def extract_remember_commands(message: str) -> List[str]:
        """Extract @remember commands from user message."""
        # Pattern: @remember followed by text until end or newline
        pattern = r'@remember\s+([^\n]+)'
        matches = re.findall(pattern, message, re.IGNORECASE)
        return [m.strip() for m in matches]

    @staticmethod
    def clean_message(message: str) -> str:
        """Remove @remember commands from message."""
        return re.sub(r'@remember\s+[^\n]+', '', message, flags=re.IGNORECASE).strip()

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
                    "description": "Search long-term memory for relevant context about the user",
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
            {
                "type": "function",
                "function": {
                    "name": "save_memory",
                    "description": """Save important information to long-term memory. Use this AUTOMATICALLY when you learn new things about the user.

Examples of when to save:
- Personal info: "User's mother is named Neeta Lad" (type: relationship)
- Preferences: "User doesn't drink alcohol" (type: preference)
- Routines: "User prefers morning meetings 9-11 AM" (type: routine)
- Facts: "User is allergic to peanuts" (type: fact)
- Relationships: "User's best friend is Sarah" (type: relationship)

IMPORTANT: Save memories proactively whenever you encounter new information about the user.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "The information to remember (clear, specific statement)",
                            },
                            "memory_type": {
                                "type": "string",
                                "enum": ["fact", "preference", "routine", "relationship", "context", "note"],
                                "description": """Type of memory:
- fact: General facts about the user
- preference: User likes/dislikes
- routine: Regular patterns or schedules
- relationship: Info about family, friends, colleagues
- context: Background or situational info
- note: General notes""",
                                "default": "fact",
                            },
                            "category": {
                                "type": "string",
                                "description": "Optional category (e.g., 'family', 'health', 'work')",
                            },
                            "importance": {
                                "type": "number",
                                "description": "Importance score 0.0-1.0 (0.5=normal, 0.8=high, 1.0=critical)",
                                "default": 0.7,
                                "minimum": 0.0,
                                "maximum": 1.0,
                            },
                        },
                        "required": ["content"],
                    },
                },
            },
        ]
