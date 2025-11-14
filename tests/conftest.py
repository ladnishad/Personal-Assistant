"""Pytest configuration and fixtures."""

import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.main import app


@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_db():
    """Create test database connection."""
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client["lifeos_test"]
    yield db
    # Cleanup
    await client.drop_database("lifeos_test")
    client.close()
