"""Memory API routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.memory.models import MemoryType
from app.memory.schemas import (
    MemoryCreate,
    MemoryListResponse,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResponse,
)
from app.memory.service import MemoryService

router = APIRouter()


@router.post("/", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    memory_data: MemoryCreate, current_user: User = Depends(get_current_active_user)
):
    """Create a new memory."""
    memory = await MemoryService.create_memory(current_user.id, memory_data)
    return MemoryResponse(
        _id=str(memory.id),
        user_id=str(memory.user_id),
        content=memory.content,
        memory_type=memory.memory_type,
        category=memory.category,
        tags=memory.tags,
        confidence=memory.confidence,
        importance=memory.importance,
        access_count=memory.access_count,
        created_at=memory.created_at,
    )


@router.post("/search", response_model=List[MemorySearchResponse])
async def search_memories(
    search_request: MemorySearchRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Semantic search across memories."""
    results = await MemoryService.semantic_search(
        user_id=current_user.id,
        query=search_request.query,
        limit=search_request.limit,
        memory_type=search_request.memory_type,
    )

    return [
        MemorySearchResponse(
            memory=MemoryResponse(
                _id=str(m.id),
                user_id=str(m.user_id),
                content=m.content,
                memory_type=m.memory_type,
                category=m.category,
                tags=m.tags,
                confidence=m.confidence,
                importance=m.importance,
                access_count=m.access_count,
                created_at=m.created_at,
            ),
            score=score,
        )
        for m, score in results
    ]


@router.get("/", response_model=MemoryListResponse)
async def list_memories(
    memory_type: Optional[MemoryType] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
):
    """List user memories."""
    skip = (page - 1) * page_size

    memories, total = await MemoryService.get_user_memories(
        user_id=current_user.id,
        memory_type=memory_type,
        skip=skip,
        limit=page_size,
    )

    memory_responses = [
        MemoryResponse(
            _id=str(m.id),
            user_id=str(m.user_id),
            content=m.content,
            memory_type=m.memory_type,
            category=m.category,
            tags=m.tags,
            confidence=m.confidence,
            importance=m.importance,
            access_count=m.access_count,
            created_at=m.created_at,
        )
        for m in memories
    ]

    return MemoryListResponse(memories=memory_responses, total=total)
