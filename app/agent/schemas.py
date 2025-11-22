"""Agent request/response schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")
    tool_calls: Optional[List[dict]] = Field(
        default=None, description="Tool calls made in this message (for assistant messages)"
    )


class AgentChatRequest(BaseModel):
    """Agent chat request."""

    message: str = Field(..., description="User message")
    context: Optional[dict] = Field(default=None, description="Additional context")
    use_memory: bool = Field(default=True, description="Whether to use long-term memory")
    conversation_id: Optional[str] = Field(
        default=None, description="Existing conversation ID to continue"
    )
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Recent conversation history for context (last 15-20 messages)",
    )
    stream_screenshots: bool = Field(
        default=False,
        description="Whether to stream screenshots from computer control agent in the response"
    )


class TaskReference(BaseModel):
    """Reference to a task that was created or updated."""

    task_id: str
    task_title: str
    action: str  # "created", "updated", "completed"


class ScreenshotCapture(BaseModel):
    """Screenshot captured during computer control agent execution."""

    timestamp: str = Field(..., description="ISO timestamp when screenshot was taken")
    screenshot: str = Field(..., description="Base64-encoded PNG image")
    width: int = Field(..., description="Screenshot width in pixels")
    height: int = Field(..., description="Screenshot height in pixels")
    action_context: Optional[str] = Field(
        default=None, description="What action was being performed (e.g., 'clicking search button')"
    )


class AgentChatResponse(BaseModel):
    """Agent chat response."""

    message: str
    conversation_id: str = Field(..., description="Conversation ID for this chat session")
    tools_used: List[str] = Field(default_factory=list)
    context_retrieved: int = Field(default=0, description="Number of memories retrieved")
    actions_taken: List[dict] = Field(default_factory=list)
    memories_saved: int = Field(default=0, description="Number of memories saved during this chat")
    task_reference: Optional[TaskReference] = Field(default=None, description="Reference to a task that was created or updated")
    screenshots: List[ScreenshotCapture] = Field(
        default_factory=list,
        description="Screenshots captured during computer control operations (if enabled)"
    )


class AgentToolCall(BaseModel):
    """Agent tool call result."""

    tool_name: str
    tool_input: dict
    tool_output: dict
