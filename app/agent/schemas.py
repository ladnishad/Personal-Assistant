"""Agent request/response schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")


class AgentChatRequest(BaseModel):
    """Agent chat request."""

    message: str = Field(..., description="User message")
    context: Optional[dict] = Field(default=None, description="Additional context")
    use_memory: bool = Field(default=True, description="Whether to use long-term memory")


class AgentChatResponse(BaseModel):
    """Agent chat response."""

    message: str
    tools_used: List[str] = Field(default_factory=list)
    context_retrieved: int = Field(default=0, description="Number of memories retrieved")
    actions_taken: List[dict] = Field(default_factory=list)


class AgentToolCall(BaseModel):
    """Agent tool call result."""

    tool_name: str
    tool_input: dict
    tool_output: dict
