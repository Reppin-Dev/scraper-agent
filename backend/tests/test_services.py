"""Tests for services."""
import pytest
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

from src.services.storage_service import StorageService
from src.services.session_manager import SessionManager
from src.models import ScrapeRequest, SessionStatus, ScrapeMode


@pytest.fixture
def temp_storage_dir():
    """Create a temporary storage directory for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def storage_service(temp_storage_dir):
    """Create a storage service instance with temp directory."""
    return StorageService(base_path=temp_storage_dir)


@pytest.fixture
def session_manager(storage_service):
    """Create a session manager instance."""
    return SessionManager(storage=storage_service)


class TestStorageService:
    """Tests for StorageService."""

    def test_generate_session_id(self, storage_service):
        """Test session ID generation."""
        session_id = storage_service.generate_session_id()
        assert isinstance(session_id, str)
        assert len(session_id) > 0
        # Should have timestamp format
        assert "_" in session_id

    def test_create_session_directory(self, storage_service):
        """Test creating a session directory."""
        session_id = "test_session_123"
        session_dir = storage_service.create_session_directory(session_id)
        assert session_dir.exists()
        assert session_dir.is_dir()

    def test_save_and_load_json(self, storage_service):
        """Test saving and loading JSON files."""
        session_id = "test_session_123"
        storage_service.create_session_directory(session_id)

        test_data = {"key": "value", "number": 42}
        storage_service.save_json(session_id, "test.json", test_data)

        loaded_data = storage_service.load_json(session_id, "test.json")
        assert loaded_data == test_data

    def test_list_sessions(self, storage_service):
        """Test listing sessions."""
        # Create multiple sessions
        session_ids = ["session_1", "session_2", "session_3"]
        for session_id in session_ids:
            storage_service.create_session_directory(session_id)

        sessions = storage_service.list_sessions()
        assert len(sessions) == 3
        # Should be sorted in reverse order
        assert sessions[0] == "session_3"

    def test_session_exists(self, storage_service):
        """Test checking if session exists."""
        session_id = "test_session"
        assert not storage_service.session_exists(session_id)

        storage_service.create_session_directory(session_id)
        assert storage_service.session_exists(session_id)

    def test_delete_session(self, storage_service):
        """Test deleting a session."""
        session_id = "test_session"
        storage_service.create_session_directory(session_id)
        storage_service.save_json(session_id, "test.json", {"data": "test"})

        assert storage_service.delete_session(session_id)
        assert not storage_service.session_exists(session_id)


class TestSessionManager:
    """Tests for SessionManager."""

    @pytest.mark.asyncio
    async def test_initialize_session(self, session_manager):
        """Test initializing a new session."""
        request = ScrapeRequest(
            url="https://example.com",
            purpose="Test scraping",
            mode=ScrapeMode.SINGLE_PAGE,
        )

        session_id, metadata = await session_manager.initialize_session(request)

        assert isinstance(session_id, str)
        assert metadata.session_id == session_id
        assert metadata.status == SessionStatus.PENDING
        assert metadata.url == str(request.url)
        assert metadata.purpose == request.purpose

    @pytest.mark.asyncio
    async def test_update_status(self, session_manager):
        """Test updating session status."""
        request = ScrapeRequest(
            url="https://example.com", purpose="Test", mode=ScrapeMode.SINGLE_PAGE
        )

        session_id, _ = await session_manager.initialize_session(request)

        # Update to in_progress
        metadata = await session_manager.update_status(
            session_id, SessionStatus.IN_PROGRESS
        )
        assert metadata.status == SessionStatus.IN_PROGRESS

        # Update to completed
        metadata = await session_manager.update_status(
            session_id, SessionStatus.COMPLETED
        )
        assert metadata.status == SessionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_save_and_get_session(self, session_manager):
        """Test saving and retrieving session data."""
        request = ScrapeRequest(
            url="https://example.com", purpose="Test", mode=ScrapeMode.SINGLE_PAGE
        )

        session_id, _ = await session_manager.initialize_session(request)

        # Save schema and data
        schema = {"fields": {"title": {"type": "string", "required": True}}}
        data = {"title": "Test Title"}

        await session_manager.save_schema(session_id, schema)
        await session_manager.save_extracted_data(session_id, data)

        # Retrieve session
        session = await session_manager.get_session(session_id)
        assert session is not None
        assert session.schema == schema
        assert session.extracted_data == data

    @pytest.mark.asyncio
    async def test_delete_session(self, session_manager):
        """Test deleting a session."""
        request = ScrapeRequest(
            url="https://example.com", purpose="Test", mode=ScrapeMode.SINGLE_PAGE
        )

        session_id, _ = await session_manager.initialize_session(request)

        # Delete session
        success = await session_manager.delete_session(session_id)
        assert success

        # Should not exist anymore
        session = await session_manager.get_session(session_id)
        assert session is None
