"""Memory service layer with vector search."""

import logging
from datetime import datetime
from typing import List, Optional

from beanie import PydanticObjectId
from openai import AsyncOpenAI

from app.config import settings
from app.memory.models import Memory, MemoryType
from app.memory.schemas import MemoryCreate

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=settings.openai_api_key)


class MemoryService:
    """Memory service with vector search capabilities."""

    @staticmethod
    async def create_memory(user_id: PydanticObjectId, memory_data: MemoryCreate) -> Memory:
        """Create a new memory with embedding."""
        # Generate embedding
        embedding = await MemoryService.generate_embedding(memory_data.content)

        # Create memory
        memory = Memory(
            user_id=user_id,
            embedding=embedding,
            embedded_at=datetime.utcnow(),
            **memory_data.model_dump(),
        )

        await memory.insert()
        logger.info(f"Memory created for user {user_id}")

        return memory

    @staticmethod
    async def generate_embedding(text: str) -> List[float]:
        """Generate embedding for text using OpenAI."""
        try:
            response = await openai_client.embeddings.create(
                model=settings.openai_embedding_model, input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    @staticmethod
    async def semantic_search(
        user_id: PydanticObjectId,
        query: str,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None,
    ) -> List[tuple[Memory, float]]:
        """Perform semantic search on memories using vector similarity."""
        # Generate query embedding
        query_embedding = await MemoryService.generate_embedding(query)

        if not query_embedding:
            return []

        # Build aggregation pipeline for vector search
        # Note: This requires MongoDB Atlas Vector Search index
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "memory_vector_index",
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": limit * 10,
                    "limit": limit,
                }
            },
            {"$match": {"user_id": user_id}},
        ]

        # Add memory type filter if specified
        if memory_type:
            pipeline[1]["$match"]["memory_type"] = memory_type

        try:
            # Execute vector search
            results = await Memory.aggregate(pipeline).to_list()

            # Convert to Memory objects with scores
            memories_with_scores = []
            for result in results:
                memory = Memory(**result)
                score = result.get("score", 0.0)
                memories_with_scores.append((memory, score))

                # Update access tracking
                memory.last_accessed = datetime.utcnow()
                memory.access_count += 1
                await memory.save()

            return memories_with_scores

        except Exception as e:
            logger.error(f"Error performing vector search: {e}")
            # Fallback to text search if vector search fails
            return await MemoryService._fallback_text_search(
                user_id, query, limit, memory_type
            )

    @staticmethod
    async def _fallback_text_search(
        user_id: PydanticObjectId,
        query: str,
        limit: int,
        memory_type: Optional[MemoryType] = None,
    ) -> List[tuple[Memory, float]]:
        """Fallback text search when vector search is unavailable."""
        query_filter = {
            "user_id": user_id,
            "content": {"$regex": query, "$options": "i"},
        }

        if memory_type:
            query_filter["memory_type"] = memory_type

        memories = await Memory.find(query_filter).limit(limit).to_list()

        # Return with default score
        return [(memory, 0.5) for memory in memories]

    @staticmethod
    async def get_user_memories(
        user_id: PydanticObjectId,
        memory_type: Optional[MemoryType] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[Memory], int]:
        """Get user memories with filters."""
        query = {"user_id": user_id}

        if memory_type:
            query["memory_type"] = memory_type

        # Get memories
        memories = (
            await Memory.find(query)
            .sort(-Memory.created_at)
            .skip(skip)
            .limit(limit)
            .to_list()
        )

        # Get total count
        total = await Memory.find(query).count()

        return memories, total
