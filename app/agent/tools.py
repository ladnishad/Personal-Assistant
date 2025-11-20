"""Agent tools for LLM function calling using OpenAI Agents SDK."""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List

from agents import WebSearchTool, function_tool
from beanie import PydanticObjectId

from app.config import settings
from app.agent.email_tools import (
    find_emails_from_sender,
    get_email_details,
    get_email_thread,
    get_emails_by_category,
    get_recent_emails,
    get_related_emails,
    get_unread_emails,
    mark_emails_read,
    scan_emails_for_packages,
    search_emails,
    star_email,
    sync_emails,
)
from app.emails.service import EmailService
from app.memory.models import MemoryType
from app.memory.schemas import MemoryCreate
from app.memory.service import MemoryService
from app.tasks.models import TaskPriority, TaskStatus
from app.tasks.schemas import TaskCreate, TaskUpdate
from app.tasks.service import TaskService

logger = logging.getLogger(__name__)


# Store user_id in context for tool functions
# This will be injected via agent context
_current_user_id: PydanticObjectId = None


def set_current_user_id(user_id: PydanticObjectId):
    """Set the current user ID for tool execution context."""
    global _current_user_id
    _current_user_id = user_id


def get_current_user_id() -> PydanticObjectId:
    """Get the current user ID from execution context."""
    global _current_user_id
    if _current_user_id is None:
        raise RuntimeError("User ID not set in execution context")
    return _current_user_id


@function_tool
async def create_task(
    title: str,
    description: str = None,
    due_date: str = None,
    priority: str = "medium",
) -> Dict[str, Any]:
    """Create a new task, todo, or reminder for the user.

    CRITICAL: Use this function WHENEVER the user asks you to:
    - Create, add, make a task/todo/reminder
    - Remember to do something
    - Track an action item
    - Set a reminder
    - Plan something (trips, events, projects)

    Examples:
    - "Create a task to review the report" → create_task(title="Review the report")
    - "Remind me to call mom tomorrow" → create_task(title="Call mom", due_date="2024-01-20")
    - "Add buy groceries to my todo list" → create_task(title="Buy groceries")
    - "I need to finish the presentation by Friday" → create_task(title="Finish presentation", due_date="Friday")
    - "Plan our trip to Austin" → create_task(title="Plan Austin trip")

    You MUST actually call this function - don't just say you created a task!

    Args:
        title: Clear, concise title for the task (required)
        description: Optional detailed description of the task
        due_date: Optional due date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        priority: Task priority level - "low", "medium", "high", or "urgent" (default: "medium")

    Returns:
        Dictionary with task ID, title, status, priority, and created flag
    """
    try:
        user_id = get_current_user_id()

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


@function_tool
async def get_tasks(status: str = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Get user's tasks.

    Use this to retrieve tasks, especially when you need to:
    - Check for existing tasks before creating new ones
    - Find a specific task to update
    - Show the user their current tasks

    Args:
        status: Filter by task status - "todo", "in_progress", "done", or "cancelled" (optional)
        limit: Maximum number of results (default: 10)

    Returns:
        List of tasks with ID, title, status, priority, and due date
    """
    try:
        user_id = get_current_user_id()
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


@function_tool
async def update_task_content(task_id: str, content: str) -> Dict[str, Any]:
    """Update a task's content with rich markdown documentation.

    Use this when:
    - User asks to work on a specific task
    - You need to add research, plans, or documentation to a task
    - Creating formatted guides, itineraries, or detailed information for a task

    IMPORTANT: Format content as markdown with proper structure:
    - Use headers (##, ###) for sections
    - Use bullet points or numbered lists
    - Include relevant details, links, pricing where applicable
    - Make it visually organized and easy to read

    Example: When user says "Let's plan our anniversary trip to Fredericksburg"
    → Research accommodations, activities, restaurants
    → Create beautiful markdown with sections
    → Call update_task_content with the formatted markdown
    → Tell user you've added the information to their task

    Args:
        task_id: The ID of the task to update
        content: Markdown-formatted content to add to the task (use proper headers, lists, formatting)

    Returns:
        Dictionary with task ID, title, content_updated flag, and content length
    """
    try:
        user_id = get_current_user_id()
        task_data = TaskUpdate(content=content)
        task = await TaskService.update_task(task_id, user_id, task_data)

        logger.info(f"Task content updated for task {task_id}")

        return {
            "id": str(task.id),
            "title": task.title,
            "content_updated": True,
            "content_length": len(content),
        }
    except Exception as e:
        logger.error(f"Error updating task content: {e}")
        return {"error": str(e), "content_updated": False}


async def _search_memory_internal(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Internal function to search long-term memory.

    This is used internally by the service layer for direct calls.
    For agent tool use, see search_memory below.

    Args:
        query: Search query for memory
        limit: Maximum number of results (default: 5)

    Returns:
        List of relevant memories with content, type, relevance score, and importance
    """
    try:
        user_id = get_current_user_id()
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


@function_tool
async def search_memory(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search long-term memory for relevant context about the user.

    Use this to recall information about the user's preferences, relationships,
    routines, and other important details.

    Args:
        query: Search query for memory
        limit: Maximum number of results (default: 5)

    Returns:
        List of relevant memories with content, type, relevance score, and importance
    """
    return await _search_memory_internal(query, limit)


async def _save_memory_internal(
    content: str,
    memory_type: str = "fact",
    category: str = None,
    importance: float = 0.7,
) -> Dict[str, Any]:
    """Internal function to save information to long-term memory.

    This is used internally by the service layer for direct calls.
    For agent tool use, see save_memory below.

    Args:
        content: The information to remember (clear, specific statement)
        memory_type: Type of memory - "fact", "preference", "routine", "relationship", "context", or "note"
        category: Optional category (e.g., "family", "health", "work")
        importance: Importance score 0.0-1.0 (0.5=normal, 0.8=high, 1.0=critical, default: 0.7)

    Returns:
        Dictionary with memory ID, content, type, and saved flag
    """
    try:
        user_id = get_current_user_id()

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


@function_tool
async def save_memory(
    content: str,
    memory_type: str = "fact",
    category: str = None,
    importance: float = 0.7,
) -> Dict[str, Any]:
    """Save important information to long-term memory.

    Use this tool AUTOMATICALLY whenever you learn new information about the user, such as:
    - Personal information (names of family, friends, pets)
    - Preferences (likes, dislikes, habits)
    - Routines (daily patterns, schedules)
    - Relationships (family members, colleagues, friends)
    - Important facts (allergies, dietary restrictions, etc.)

    Examples of when to save:
    - Personal info: "User's mother is named Neeta Lad" (type: "relationship")
    - Preferences: "User doesn't drink alcohol" (type: "preference")
    - Routines: "User prefers morning meetings 9-11 AM" (type: "routine")
    - Facts: "User is allergic to peanuts" (type: "fact")
    - Relationships: "User's best friend is Sarah" (type: "relationship")

    IMPORTANT: Save memories proactively whenever you encounter new information about the user.

    Args:
        content: The information to remember (clear, specific statement)
        memory_type: Type of memory - "fact", "preference", "routine", "relationship", "context", or "note"
            - fact: General facts about the user
            - preference: User likes/dislikes
            - routine: Regular patterns or schedules
            - relationship: Info about family, friends, colleagues
            - context: Background or situational info
            - note: General notes
        category: Optional category (e.g., "family", "health", "work")
        importance: Importance score 0.0-1.0 (0.5=normal, 0.8=high, 1.0=critical, default: 0.7)

    Returns:
        Dictionary with memory ID, content, type, and saved flag
    """
    return await _save_memory_internal(content, memory_type, category, importance)


# Utility functions (not tools)
def extract_remember_commands(message: str) -> List[str]:
    """Extract @remember commands from user message."""
    # Pattern: @remember followed by text until end or newline
    pattern = r'@remember\s+([^\n]+)'
    matches = re.findall(pattern, message, re.IGNORECASE)
    return [m.strip() for m in matches]


def clean_message(message: str) -> str:
    """Remove @remember commands from message."""
    return re.sub(r'@remember\s+[^\n]+', '', message, flags=re.IGNORECASE).strip()


# List of all agent tools
AGENT_TOOLS = [
    # Email management tools
    get_email_details,
    get_recent_emails,
    search_emails,
    get_emails_by_category,
    find_emails_from_sender,
    get_unread_emails,
    mark_emails_read,
    star_email,
    sync_emails,
    get_email_thread,
    get_related_emails,
    scan_emails_for_packages,
    # Task management tools
    create_task,
    get_tasks,
    update_task_content,
    # Search and memory tools
    WebSearchTool(),  # Built-in OpenAI web search (no external API needed)
    search_memory,
    save_memory,
]
