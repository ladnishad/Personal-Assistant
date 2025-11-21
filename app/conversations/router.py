"""Conversation API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.conversations.models import Conversation, ConversationMessage
from app.conversations.schemas import (
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
    ConversationWithMessages,
    MessageResponse,
)

router = APIRouter()


@router.get("/", response_model=ConversationListResponse)
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
):
    """List user's conversations."""
    skip = (page - 1) * page_size

    # Get conversations sorted by most recent
    conversations = (
        await Conversation.find(Conversation.user_id == current_user.id)
        .sort(-Conversation.updated_at)
        .skip(skip)
        .limit(page_size)
        .to_list()
    )

    total = await Conversation.find(Conversation.user_id == current_user.id).count()

    conversation_responses = [
        ConversationResponse(
            id=str(c.id),
            user_id=str(c.user_id),
            title=c.title,
            message_count=c.message_count,
            is_active=c.is_active,
            task_id=str(c.task_id) if c.task_id else None,
            summary=c.summary,
            summary_updated_at=c.summary_updated_at,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in conversations
    ]

    return ConversationListResponse(conversations=conversation_responses, total=total)


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: str, current_user: User = Depends(get_current_active_user)
):
    """Get a conversation with its full message history."""
    # Get conversation
    conversation = await Conversation.get(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    # Verify ownership
    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this conversation",
        )

    # Get all messages for this conversation
    messages = (
        await ConversationMessage.find(
            ConversationMessage.conversation_id == conversation.id
        )
        .sort(ConversationMessage.timestamp)
        .to_list()
    )

    message_responses = [
        MessageResponse(
            id=str(m.id),
            conversation_id=str(m.conversation_id),
            role=m.role,
            content=m.content,
            tool_calls=m.tool_calls,
            tokens_used=m.tokens_used,
            timestamp=m.timestamp,
        )
        for m in messages
    ]

    return ConversationWithMessages(
        id=str(conversation.id),
        user_id=str(conversation.user_id),
        title=conversation.title,
        message_count=conversation.message_count,
        is_active=conversation.is_active,
        task_id=str(conversation.task_id) if conversation.task_id else None,
        summary=conversation.summary,
        summary_updated_at=conversation.summary_updated_at,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=message_responses,
    )


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    update_data: ConversationUpdate,
    current_user: User = Depends(get_current_active_user),
):
    """Update a conversation (e.g., rename, archive)."""
    conversation = await Conversation.get(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    # Verify ownership
    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this conversation",
        )

    # Update fields
    if update_data.title is not None:
        conversation.title = update_data.title
    if update_data.is_active is not None:
        conversation.is_active = update_data.is_active

    from datetime import datetime

    conversation.updated_at = datetime.utcnow()
    await conversation.save()

    return ConversationResponse(
        id=str(conversation.id),
        user_id=str(conversation.user_id),
        title=conversation.title,
        message_count=conversation.message_count,
        is_active=conversation.is_active,
        task_id=str(conversation.task_id) if conversation.task_id else None,
        summary=conversation.summary,
        summary_updated_at=conversation.summary_updated_at,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.get("/by-task/{task_id}", response_model=ConversationWithMessages)
async def get_conversation_by_task(
    task_id: str, current_user: User = Depends(get_current_active_user)
):
    """Get a conversation linked to a specific task."""
    from beanie import PydanticObjectId

    # Find conversation by task_id
    conversation = await Conversation.find_one(
        Conversation.task_id == PydanticObjectId(task_id),
        Conversation.user_id == current_user.id,
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No conversation found for this task",
        )

    # Get all messages for this conversation
    messages = (
        await ConversationMessage.find(
            ConversationMessage.conversation_id == conversation.id
        )
        .sort(ConversationMessage.timestamp)
        .to_list()
    )

    message_responses = [
        MessageResponse(
            id=str(m.id),
            conversation_id=str(m.conversation_id),
            role=m.role,
            content=m.content,
            tool_calls=m.tool_calls,
            tokens_used=m.tokens_used,
            timestamp=m.timestamp,
        )
        for m in messages
    ]

    return ConversationWithMessages(
        id=str(conversation.id),
        user_id=str(conversation.user_id),
        title=conversation.title,
        message_count=conversation.message_count,
        is_active=conversation.is_active,
        task_id=str(conversation.task_id) if conversation.task_id else None,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=message_responses,
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str, current_user: User = Depends(get_current_active_user)
):
    """Delete a conversation and all its messages."""
    conversation = await Conversation.get(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    # Verify ownership
    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this conversation",
        )

    # Delete all messages first
    await ConversationMessage.find(
        ConversationMessage.conversation_id == conversation.id
    ).delete()

    # Delete conversation
    await conversation.delete()

    return None
