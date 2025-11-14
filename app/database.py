"""MongoDB database connection and initialization."""

import logging
from typing import Optional

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

logger = logging.getLogger(__name__)


class Database:
    """MongoDB database manager."""

    client: Optional[AsyncIOMotorClient] = None
    db = None

    @classmethod
    async def connect_db(cls):
        """Initialize MongoDB connection and Beanie ODM."""
        try:
            logger.info(f"Connecting to MongoDB at {settings.mongodb_url}")

            cls.client = AsyncIOMotorClient(
                settings.mongodb_url,
                minPoolSize=settings.mongodb_min_pool_size,
                maxPoolSize=settings.mongodb_max_pool_size,
            )

            cls.db = cls.client[settings.mongodb_db_name]

            # Import all document models for Beanie
            from app.auth.models import User
            from app.calendar.models import CalendarEvent
            from app.emails.models import Email
            from app.integrations.models import Integration
            from app.memory.models import Memory
            from app.tasks.models import Task

            # Initialize Beanie with all document models
            await init_beanie(
                database=cls.db,
                document_models=[
                    User,
                    Integration,
                    Email,
                    CalendarEvent,
                    Task,
                    Memory,
                ],
            )

            logger.info("Successfully connected to MongoDB and initialized Beanie")

            # Create indexes
            await cls._create_indexes()

        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            raise

    @classmethod
    async def _create_indexes(cls):
        """Create database indexes for optimal performance."""
        try:
            # User indexes
            await cls.db.users.create_index("email", unique=True)

            # Email indexes
            await cls.db.emails.create_index([("user_id", 1), ("received_at", -1)])
            await cls.db.emails.create_index([("user_id", 1), ("is_read", 1)])
            await cls.db.emails.create_index("message_id", unique=True)

            # Task indexes
            await cls.db.tasks.create_index([("user_id", 1), ("status", 1)])
            await cls.db.tasks.create_index([("user_id", 1), ("due_date", 1)])

            # Calendar event indexes
            await cls.db.calendar_events.create_index([("user_id", 1), ("start_time", 1)])
            await cls.db.calendar_events.create_index("event_id", unique=True)

            # Memory indexes (for vector search - will be created in Atlas)
            await cls.db.memories.create_index([("user_id", 1), ("created_at", -1)])
            await cls.db.memories.create_index([("user_id", 1), ("memory_type", 1)])

            logger.info("Database indexes created successfully")

        except Exception as e:
            logger.warning(f"Error creating indexes: {e}")

    @classmethod
    async def close_db(cls):
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed")


# Database instance
db = Database()
