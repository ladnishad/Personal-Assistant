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
    async def _cleanup_conflicting_indexes(cls):
        """Drop specific conflicting indexes that prevent Beanie initialization.

        This removes auto-generated indexes that conflict with our explicit
        index definitions (e.g., indexes with same name but different specs).
        """
        collections_to_clean = {
            "emails": ["message_id_1"],
            "calendar_events": ["event_id_1"],
        }

        for collection_name, index_names in collections_to_clean.items():
            collection = cls.db[collection_name]

            for index_name in index_names:
                try:
                    await collection.drop_index(index_name)
                    logger.info(
                        f"Dropped conflicting index '{index_name}' from '{collection_name}'"
                    )
                except Exception as e:
                    # Index might not exist, which is fine
                    logger.debug(
                        f"Could not drop index '{index_name}' from '{collection_name}': {e}"
                    )

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

            # Clean up conflicting indexes before Beanie initialization
            await cls._cleanup_conflicting_indexes()

            # Import all document models for Beanie
            from app.auth.models import User
            from app.calendar.models import CalendarEvent
            from app.confirmations.document import Confirmation
            from app.conversations.models import Conversation, ConversationMessage
            from app.emails.models import Email
            from app.emails.relationships import EmailRelationship
            from app.integrations.models import Integration
            from app.memory.models import Memory
            from app.packages.models import Package
            from app.tasks.models import Task

            # Initialize Beanie with all document models
            await init_beanie(
                database=cls.db,
                document_models=[
                    User,
                    Integration,
                    Email,
                    EmailRelationship,  # Email relationship graph for package tracking
                    CalendarEvent,
                    Task,
                    Memory,
                    Conversation,
                    ConversationMessage,
                    Package,  # Package model for tracking with email relationships
                    Confirmation,  # User confirmations for agent safety checks
                ],
            )

            logger.info("Successfully connected to MongoDB and initialized Beanie")
            logger.info("Database indexes created automatically by Beanie")

        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            raise

    @classmethod
    async def close_db(cls):
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed")


# Database instance
db = Database()
