"""Memory service layer with vector search."""

import logging
import re
from datetime import datetime
from typing import List, Optional

import numpy as np
from beanie import PydanticObjectId
from openai import AsyncOpenAI

from app.config import settings
from app.memory.models import Memory, MemoryType
from app.memory.schemas import MemoryCreate

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

# Stop words to exclude from keyword extraction
STOP_WORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "what",
    "who",
    "when",
    "where",
    "why",
    "how",
    "do",
    "does",
    "did",
    "you",
    "your",
    "my",
    "me",
    "i",
    "about",
    "know",
    "tell",
    "can",
}


class MemoryService:
    """Memory service with vector search capabilities."""

    @staticmethod
    def _extract_keywords(query: str) -> List[str]:
        """Extract meaningful keywords from search query."""
        # Convert to lowercase and extract words
        words = re.findall(r"\b\w+\b", query.lower())

        # Filter out stop words and short words
        keywords = [w for w in words if w not in STOP_WORDS and len(w) > 2]

        # Return unique keywords
        return list(set(keywords))

    @staticmethod
    def _calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0

        try:
            arr1 = np.array(vec1)
            arr2 = np.array(vec2)

            # Calculate cosine similarity
            dot_product = np.dot(arr1, arr2)
            norm1 = np.linalg.norm(arr1)
            norm2 = np.linalg.norm(arr2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0

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
        logger.info(f"Starting semantic search for user {user_id} with query: '{query}'")

        # Generate query embedding
        query_embedding = await MemoryService.generate_embedding(query)

        if not query_embedding:
            logger.warning("Failed to generate query embedding, using fallback search")
            return await MemoryService._fallback_text_search(
                user_id, query, limit, memory_type
            )

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
            logger.info("Attempting MongoDB Atlas vector search...")
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

            logger.info(f"Vector search succeeded, found {len(memories_with_scores)} memories")
            return memories_with_scores

        except Exception as e:
            logger.warning(
                f"Vector search failed (MongoDB Atlas not configured or index missing): {e}"
            )
            logger.info("Falling back to keyword-based search with cosine similarity...")
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
        """Fallback search when vector search is unavailable.

        Uses a multi-strategy approach:
        1. Keyword-based search with OR queries
        2. Cosine similarity on embeddings (if available)
        3. Combines and ranks results
        """
        logger.info(f"Using fallback search for query: '{query}'")

        # Extract keywords from query
        keywords = MemoryService._extract_keywords(query)
        logger.info(f"Extracted keywords: {keywords}")

        # Build base filter
        base_filter = {"user_id": user_id}
        if memory_type:
            base_filter["memory_type"] = memory_type

        # Strategy 1: Keyword-based search with OR
        if keywords:
            # Create regex patterns for each keyword (case-insensitive)
            keyword_patterns = [
                {"content": {"$regex": keyword, "$options": "i"}}
                for keyword in keywords
            ]

            # Combine with OR
            query_filter = {
                **base_filter,
                "$or": keyword_patterns
            }

            # Get more than we need for ranking
            memories = await Memory.find(query_filter).limit(limit * 3).to_list()
            logger.info(f"Keyword search found {len(memories)} memories")
        else:
            # No keywords, get recent memories
            memories = await Memory.find(base_filter).sort(-Memory.created_at).limit(limit * 2).to_list()
            logger.info(f"No keywords extracted, retrieved {len(memories)} recent memories")

        if not memories:
            logger.warning("No memories found with fallback search")
            return []

        # Strategy 2: Generate query embedding and use cosine similarity
        query_embedding = await MemoryService.generate_embedding(query)

        memories_with_scores = []

        for memory in memories:
            score = 0.0

            # Calculate similarity score if embeddings exist
            if query_embedding and memory.embedding:
                # Use cosine similarity
                similarity = MemoryService._calculate_cosine_similarity(
                    query_embedding, memory.embedding
                )
                score = similarity
                logger.debug(f"Memory '{memory.content[:50]}...' similarity: {similarity:.3f}")
            else:
                # Fallback: count keyword matches
                content_lower = memory.content.lower()
                matches = sum(1 for kw in keywords if kw in content_lower)
                score = matches / max(len(keywords), 1) if keywords else 0.5
                logger.debug(f"Memory '{memory.content[:50]}...' keyword score: {score:.3f}")

            # Boost by importance
            final_score = score * (0.7 + 0.3 * memory.importance)

            memories_with_scores.append((memory, final_score))

            # Update access tracking
            memory.last_accessed = datetime.utcnow()
            memory.access_count += 1
            await memory.save()

        # Sort by score descending and limit
        memories_with_scores.sort(key=lambda x: x[1], reverse=True)
        results = memories_with_scores[:limit]

        logger.info(f"Returning {len(results)} memories with scores: {[f'{s:.3f}' for _, s in results]}")

        return results

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
