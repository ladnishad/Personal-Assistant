"""Agent API routes."""

from fastapi import APIRouter, Depends

from app.agent.schemas import AgentChatRequest, AgentChatResponse
from app.agent.service import AgentService
from app.auth.dependencies import get_current_active_user
from app.auth.models import User

router = APIRouter()


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(
    request: AgentChatRequest, current_user: User = Depends(get_current_active_user)
):
    """Chat with the AI agent orchestrator."""
    result = await AgentService.chat(
        user_id=current_user.id,
        message=request.message,
        use_memory=request.use_memory,
    )

    return AgentChatResponse(**result)
