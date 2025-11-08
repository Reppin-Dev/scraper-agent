"""Storage service for managing session data on the file system."""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import uuid

from ..config import settings
from ..models import Session, SessionMetadata


class StorageService:
    """Service for managing session storage on the file system."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize the storage service.

        Args:
            base_path: Base directory for storage. Defaults to settings.storage_path
        """
        self.base_path = base_path or settings.storage_path
        self._ensure_base_directory()

    def _ensure_base_directory(self) -> None:
        """Ensure the base storage directory exists."""
        self.base_path.mkdir(parents=True, exist_ok=True)

    def generate_session_id(self) -> str:
        """Generate a unique session ID with timestamp.

        Returns:
            Session ID in format: YYYYMMDD_HHMMSS_{uuid}
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        return f"{timestamp}_{unique_id}"

    def get_session_directory(self, session_id: str) -> Path:
        """Get the directory path for a session.

        Args:
            session_id: The session identifier

        Returns:
            Path to the session directory
        """
        return self.base_path / session_id

    def create_session_directory(self, session_id: str) -> Path:
        """Create a new session directory.

        Args:
            session_id: The session identifier

        Returns:
            Path to the created session directory
        """
        session_dir = self.get_session_directory(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def save_json(self, session_id: str, filename: str, data: Dict[str, Any]) -> Path:
        """Save JSON data to a file in the session directory.

        Args:
            session_id: The session identifier
            filename: Name of the file (e.g., 'metadata.json')
            data: Data to save

        Returns:
            Path to the saved file
        """
        session_dir = self.get_session_directory(session_id)
        file_path = session_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        return file_path

    def load_json(self, session_id: str, filename: str) -> Optional[Dict[str, Any]]:
        """Load JSON data from a file in the session directory.

        Args:
            session_id: The session identifier
            filename: Name of the file (e.g., 'metadata.json')

        Returns:
            Loaded data or None if file doesn't exist
        """
        session_dir = self.get_session_directory(session_id)
        file_path = session_dir / filename

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_metadata(self, session_id: str, metadata: SessionMetadata) -> Path:
        """Save session metadata.

        Args:
            session_id: The session identifier
            metadata: Session metadata to save

        Returns:
            Path to the saved file
        """
        return self.save_json(session_id, "metadata.json", metadata.model_dump())

    def load_metadata(self, session_id: str) -> Optional[SessionMetadata]:
        """Load session metadata.

        Args:
            session_id: The session identifier

        Returns:
            Session metadata or None if not found
        """
        data = self.load_json(session_id, "metadata.json")
        if data:
            return SessionMetadata(**data)
        return None

    def save_request_data(self, session_id: str, request_data: Dict[str, Any]) -> Path:
        """Save the original request data.

        Args:
            session_id: The session identifier
            request_data: Request data to save

        Returns:
            Path to the saved file
        """
        return self.save_json(session_id, "request.json", request_data)

    def load_request_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load the original request data.

        Args:
            session_id: The session identifier

        Returns:
            Request data or None if not found
        """
        return self.load_json(session_id, "request.json")

    def save_schema(self, session_id: str, schema: Dict[str, Any]) -> Path:
        """Save the extraction schema.

        Args:
            session_id: The session identifier
            schema: Schema to save

        Returns:
            Path to the saved file
        """
        return self.save_json(session_id, "schema.json", schema)

    def load_schema(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load the extraction schema.

        Args:
            session_id: The session identifier

        Returns:
            Schema or None if not found
        """
        return self.load_json(session_id, "schema.json")

    def save_extracted_data(self, session_id: str, data: Dict[str, Any]) -> Path:
        """Save the extracted data.

        Args:
            session_id: The session identifier
            data: Extracted data to save

        Returns:
            Path to the saved file
        """
        return self.save_json(session_id, "extracted_data.json", data)

    def load_extracted_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load the extracted data.

        Args:
            session_id: The session identifier

        Returns:
            Extracted data or None if not found
        """
        return self.load_json(session_id, "extracted_data.json")

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load complete session data.

        Args:
            session_id: The session identifier

        Returns:
            Complete session data or None if not found
        """
        metadata = self.load_metadata(session_id)
        if not metadata:
            return None

        request_data = self.load_request_data(session_id) or {}
        schema = self.load_schema(session_id)
        extracted_data = self.load_extracted_data(session_id)

        # Load sources if available
        sources_data = self.load_json(session_id, "sources.json")
        sources = sources_data.get("sources", []) if sources_data else []

        return Session(
            metadata=metadata,
            request_data=request_data,
            schema=schema,
            extracted_data=extracted_data,
            sources=sources,
        )

    def list_sessions(self) -> List[str]:
        """List all session IDs.

        Returns:
            List of session IDs sorted by creation time (newest first)
        """
        if not self.base_path.exists():
            return []

        sessions = [
            d.name
            for d in self.base_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

        # Sort by timestamp in session ID (newest first)
        sessions.sort(reverse=True)
        return sessions

    def session_exists(self, session_id: str) -> bool:
        """Check if a session directory exists.

        Args:
            session_id: The session identifier

        Returns:
            True if session exists, False otherwise
        """
        return self.get_session_directory(session_id).exists()

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its data.

        Args:
            session_id: The session identifier

        Returns:
            True if deleted successfully, False if session didn't exist
        """
        session_dir = self.get_session_directory(session_id)
        if not session_dir.exists():
            return False

        # Delete all files in the session directory
        for file_path in session_dir.iterdir():
            if file_path.is_file():
                file_path.unlink()

        # Delete the directory
        session_dir.rmdir()
        return True


# Global storage service instance
storage_service = StorageService()
