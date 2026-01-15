"""API endpoint tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint returns service info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert data["service"] == "Media Converter"


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test health endpoint returns status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "libreoffice_available" in data
    assert "poppler_available" in data


@pytest.mark.asyncio
async def test_convert_missing_file(client: AsyncClient):
    """Test conversion endpoint rejects request without file."""
    response = await client.post("/api/v1/convert/pptx-to-image")
    assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.asyncio
async def test_convert_invalid_file_type(client: AsyncClient):
    """Test conversion endpoint rejects invalid file types."""
    response = await client.post(
        "/api/v1/convert/pptx-to-image",
        files={"file": ("test.txt", b"not a pptx file", "text/plain")},
    )
    assert response.status_code == 400
    data = response.json()
    assert "Invalid file type" in data["detail"]


@pytest.mark.asyncio
async def test_job_status_not_found(client: AsyncClient):
    """Test job status endpoint returns 404 for unknown job."""
    response = await client.get("/api/v1/convert/status/nonexistent-job-id")
    assert response.status_code == 404
