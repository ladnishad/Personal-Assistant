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
    task_id: Optional[str] = Field(
        default=None, description="Task ID to link this conversation to"
    )
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Recent conversation history for context (last 15-20 messages)",
    )


class TaskReference(BaseModel):
    """Reference to a task that was created or updated."""

    task_id: str
    task_title: str
    action: str  # "created", "updated", "completed"


class AgentChatResponse(BaseModel):
    """Agent chat response."""

    message: str
    conversation_id: str = Field(..., description="Conversation ID for this chat session")
    tools_used: List[str] = Field(default_factory=list)
    context_retrieved: int = Field(default=0, description="Number of memories retrieved")
    actions_taken: List[dict] = Field(default_factory=list)
    memories_saved: int = Field(default=0, description="Number of memories saved during this chat")
    task_reference: Optional[TaskReference] = Field(default=None, description="Reference to a task that was created or updated")


class AgentToolCall(BaseModel):
    """Agent tool call result."""

    tool_name: str
    tool_input: dict
    tool_output: dict


# Streaming event schemas
class StreamEventBase(BaseModel):
    """Base class for streaming events."""

    event: str = Field(..., description="Event type")


class AgentStatusEvent(StreamEventBase):
    """Agent status update event."""

    event: str = "agent_status"
    status: str = Field(..., description="Current agent status: thinking, calling_tool, processing")
    message: Optional[str] = Field(default=None, description="Human-readable status message")


class ToolCallEvent(StreamEventBase):
    """Tool call initiated event."""

    event: str = "tool_call"
    tool_name: str = Field(..., description="Name of the tool being called")
    tool_args: dict = Field(default_factory=dict, description="Arguments passed to the tool")
    call_id: str = Field(..., description="Unique call ID")


class ToolResultEvent(StreamEventBase):
    """Tool execution result event."""

    event: str = "tool_result"
    tool_name: str = Field(..., description="Name of the tool that completed")
    call_id: str = Field(..., description="Unique call ID")
    result: Optional[str] = Field(default=None, description="Tool execution result")


class MessageDeltaEvent(StreamEventBase):
    """Message delta (partial) event."""

    event: str = "message_delta"
    delta: str = Field(..., description="Partial message content")


class MessageCompleteEvent(StreamEventBase):
    """Message complete event."""

    event: str = "message_complete"
    message: str = Field(..., description="Complete message content")


class StreamDoneEvent(StreamEventBase):
    """Stream complete event."""

    event: str = "done"
    conversation_id: str = Field(..., description="Conversation ID")
    tools_used: List[str] = Field(default_factory=list)
    context_retrieved: int = Field(default=0)
    actions_taken: List[dict] = Field(default_factory=list)
    memories_saved: int = Field(default=0)
    task_reference: Optional[TaskReference] = Field(default=None)
