"""Tests for agents."""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.agents.schema_generator import SchemaGenerator
from src.agents.content_extractor import ContentExtractor
from src.models import ScrapeRequest, ScrapeMode


class TestSchemaGenerator:
    """Tests for SchemaGenerator."""

    def test_extract_schema_valid_json(self):
        """Test extracting valid JSON schema from response."""
        generator = SchemaGenerator()

        response_text = """
        Here is the schema:
        {
            "fields": {
                "title": {
                    "type": "string",
                    "required": true,
                    "description": "Page title"
                }
            }
        }
        """

        schema = generator._extract_schema(response_text)
        assert schema is not None
        assert "fields" in schema
        assert "title" in schema["fields"]

    def test_extract_schema_invalid_json(self):
        """Test extracting invalid JSON returns None."""
        generator = SchemaGenerator()

        response_text = "This is not valid JSON"
        schema = generator._extract_schema(response_text)
        assert schema is None

    def test_build_prompt(self):
        """Test building the schema generation prompt."""
        generator = SchemaGenerator()

        purpose = "Extract contact info"
        html = "<html><body><p>Contact: test@example.com</p></body></html>"

        prompt = generator._build_prompt(purpose, html)
        assert "contact info" in prompt.lower()
        assert html in prompt
        assert "json" in prompt.lower()


class TestContentExtractor:
    """Tests for ContentExtractor."""

    def test_extract_data_valid_json(self):
        """Test extracting valid JSON data from response."""
        extractor = ContentExtractor()

        response_text = """
        {
            "title": "Test Page",
            "email": "test@example.com"
        }
        """

        data = extractor._extract_data(response_text)
        assert data is not None
        assert "title" in data
        assert data["title"] == "Test Page"

    def test_extract_data_invalid_json(self):
        """Test extracting invalid JSON returns None."""
        extractor = ContentExtractor()

        response_text = "Not valid JSON"
        data = extractor._extract_data(response_text)
        assert data is None

    def test_build_prompt(self):
        """Test building the extraction prompt."""
        extractor = ContentExtractor()

        html = "<html><body><h1>Test</h1></body></html>"
        schema = {
            "fields": {"title": {"type": "string", "required": True}}
        }

        prompt = extractor._build_prompt(html, schema)
        assert html in prompt
        assert "title" in prompt.lower()
        assert "json" in prompt.lower()


@pytest.mark.asyncio
class TestOrchestratorIntegration:
    """Integration tests for OrchestratorAgent."""

    async def test_orchestrator_workflow_mocked(self):
        """Test orchestrator workflow with mocked dependencies."""
        from src.agents.orchestrator import OrchestratorAgent
        from src.services import SessionManager, StorageService
        from pathlib import Path
        import tempfile

        # Create temp storage
        temp_dir = Path(tempfile.mkdtemp())
        storage = StorageService(base_path=temp_dir)
        session_mgr = SessionManager(storage=storage)

        # Mock the Claude API calls
        mock_schema_gen = Mock()
        mock_schema_gen.generate_schema = AsyncMock(
            return_value=({"fields": {"title": {"type": "string"}}}, None)
        )

        mock_content_ext = Mock()
        mock_content_ext.extract_content = AsyncMock(
            return_value=({"title": "Test Title"}, None)
        )

        orchestrator = OrchestratorAgent(
            session_mgr=session_mgr,
            schema_gen=mock_schema_gen,
            content_ext=mock_content_ext,
        )

        # Mock HTTP client
        with patch("src.agents.orchestrator.HTTPClient") as mock_http:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.fetch_url = AsyncMock(
                return_value=("<html><body>Test</body></html>", None)
            )
            mock_http.return_value = mock_client

            # Create request
            request = ScrapeRequest(
                url="https://example.com",
                purpose="Test extraction",
                mode=ScrapeMode.SINGLE_PAGE,
            )

            # Execute
            session_id, success = await orchestrator.execute_scrape(request)

            # Verify
            assert success
            assert session_id is not None

            # Check session was created
            session = await session_mgr.get_session(session_id)
            assert session is not None
            assert session.metadata.status.value == "completed"

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)
