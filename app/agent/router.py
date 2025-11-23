"""Agent API routes."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.agent.schemas import AgentChatRequest, AgentChatResponse
from app.agent.service import AgentService
from app.auth.dependencies import get_current_active_user
from app.auth.models import User

router = APIRouter()


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(
    request: AgentChatRequest, current_user: User = Depends(get_current_active_user)
):
    """Chat with the AI agent orchestrator using OpenAI Agents SDK.

    The agent automatically:
    - Executes tools as needed (tasks, emails, memory, web search, computer control)
    - Manages conversation history via Sessions (stored in MongoDB)
    - Applies guardrails for validation
    - Traces execution for debugging
    - Optionally streams screenshots from computer control operations (if stream_screenshots=true)
    """
    # Note: conversation_history in request is kept for backward compatibility
    # but is now ignored. The Session handles history automatically from MongoDB.
    result = await AgentService.chat(
        user=current_user,
        message=request.message,
        use_memory=request.use_memory,
        conversation_id=request.conversation_id,
        task_id=request.task_id,
        conversation_history=None,  # Not used with Agents SDK Session
        stream_screenshots=request.stream_screenshots,
    )

    return AgentChatResponse(**result)


@router.post("/chat/stream")
async def chat_with_agent_streamed(
    request: AgentChatRequest, current_user: User = Depends(get_current_active_user)
):
    """Chat with the AI agent with Server-Sent Events (SSE) streaming.

    Provides real-time updates as the agent:
    - Processes the request
    - Calls tools
    - Generates the response

    Returns a stream of events:
    - agent_status: Current agent activity
    - tool_call: When a tool is invoked
    - tool_result: When a tool completes
    - screenshot_capture: Screenshots from computer control (if stream_screenshots=true)
    - message_delta: Incremental message content
    - message_complete: Final complete message
    - done: Stream complete with metadata
    """
    return StreamingResponse(
        AgentService.chat_streamed(
            user=current_user,
            message=request.message,
            use_memory=request.use_memory,
            conversation_id=request.conversation_id,
            task_id=request.task_id,
            stream_screenshots=request.stream_screenshots,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable proxy buffering
        },
    )
