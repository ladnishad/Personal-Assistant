"""Tests for authentication module."""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Test root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "LifeOS" in response.json()["message"]


# Additional tests would go here
# - Test user registration
# - Test user login
# - Test token refresh
# - Test protected endpoints
