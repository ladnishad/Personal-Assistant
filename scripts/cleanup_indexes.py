"""Database index cleanup script.

This script drops all indexes from MongoDB collections to prevent conflicts
when Beanie recreates them with updated specifications.

Run this before starting the application if you encounter index conflicts.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings


async def cleanup_indexes():
    """Drop all indexes except _id from all collections."""
    print(f"Connecting to MongoDB at {settings.mongodb_url}...")

    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db_name]

    # List of collections to clean
    collections = [
        "users",
        "integrations",
        "emails",
        "calendar_events",
        "tasks",
        "memories",
    ]

    print("\nDropping indexes from collections...")

    for collection_name in collections:
        collection = db[collection_name]

        # Get all indexes
        indexes = await collection.list_indexes().to_list(length=100)

        print(f"\n{collection_name}:")
        for index in indexes:
            index_name = index.get("name")

            # Never drop the _id index
            if index_name == "_id_":
                print(f"  ✓ Keeping {index_name} (required)")
                continue

            try:
                await collection.drop_index(index_name)
                print(f"  ✗ Dropped {index_name}")
            except Exception as e:
                print(f"  ⚠ Failed to drop {index_name}: {e}")

    print("\n✅ Index cleanup complete!")
    print("Beanie will recreate all indexes on next startup.\n")

    client.close()


if __name__ == "__main__":
    asyncio.run(cleanup_indexes())
