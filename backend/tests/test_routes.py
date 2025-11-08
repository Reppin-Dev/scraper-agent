"""Tests for API routes."""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import shutil

from src.main import app
from src.services import storage_service
from src.models import ScrapeMode


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def temp_storage(monkeypatch):
    """Use temporary storage for all tests."""
    temp_dir = Path(tempfile.mkdtemp())
    monkeypatch.setattr(storage_service, "base_path", temp_dir)
    storage_service._ensure_base_directory()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestHealthEndpoints:
    """Tests for health and root endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data


class TestScrapeEndpoint:
    """Tests for scraping endpoint."""

    def test_create_scrape_session(self, client):
        """Test creating a scrape session."""
        request_data = {
            "url": "https://example.com",
            "purpose": "Extract contact information",
            "mode": "single-page",
        }

        response = client.post("/api/scrape", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert "session_id" in data
        assert data["status"] == "pending"
        assert "message" in data
        assert "websocket_url" in data

    def test_create_scrape_session_with_schema(self, client):
        """Test creating a scrape session with custom schema."""
        request_data = {
            "url": "https://example.com",
            "purpose": "Extract data",
            "mode": "single-page",
            "schema": {
                "fields": {"title": {"type": "string", "required": True}}
            },
        }

        response = client.post("/api/scrape", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert "session_id" in data

    def test_invalid_url(self, client):
        """Test with invalid URL."""
        request_data = {
            "url": "not-a-valid-url",
            "purpose": "Test",
            "mode": "single-page",
        }

        response = client.post("/api/scrape", json=request_data)
        assert response.status_code == 422  # Validation error


class TestSessionEndpoints:
    """Tests for session management endpoints."""

    def test_list_sessions_empty(self, client):
        """Test listing sessions when none exist."""
        response = client.get("/api/sessions")
        assert response.status_code == 200

        data = response.json()
        assert "sessions" in data
        assert "total" in data
        assert data["total"] == 0

    def test_get_session_not_found(self, client):
        """Test getting a non-existent session."""
        response = client.get("/api/sessions/nonexistent_id")
        assert response.status_code == 404

    def test_delete_session_not_found(self, client):
        """Test deleting a non-existent session."""
        response = client.delete("/api/sessions/nonexistent_id")
        assert response.status_code == 404

    def test_full_session_workflow(self, client):
        """Test complete session workflow: create, list, get, delete."""
        # Create session
        request_data = {
            "url": "https://example.com",
            "purpose": "Test",
            "mode": "single-page",
        }
        create_response = client.post("/api/scrape", json=request_data)
        assert create_response.status_code == 200
        session_id = create_response.json()["session_id"]

        # List sessions
        list_response = client.get("/api/sessions")
        assert list_response.status_code == 200
        assert list_response.json()["total"] >= 1

        # Get specific session
        get_response = client.get(f"/api/sessions/{session_id}")
        assert get_response.status_code == 200
        session_data = get_response.json()
        assert session_data["session_id"] == session_id
        # HttpUrl adds trailing slash
        assert session_data["url"] in ["https://example.com", "https://example.com/"]

        # Delete session
        delete_response = client.delete(f"/api/sessions/{session_id}")
        assert delete_response.status_code == 200

        # Verify deletion
        get_response = client.get(f"/api/sessions/{session_id}")
        assert get_response.status_code == 404
