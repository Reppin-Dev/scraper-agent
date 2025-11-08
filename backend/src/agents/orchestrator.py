"""Main orchestrator agent for coordinating the scraping workflow."""
from typing import Optional, Callable, Any
import asyncio

from ..models import ScrapeRequest, SessionStatus
from ..services import SessionManager, session_manager, HTTPClient
from .schema_generator import SchemaGenerator, schema_generator
from .content_extractor import ContentExtractor, content_extractor


class OrchestratorAgent:
    """Main agent that orchestrates the entire scraping workflow."""

    def __init__(
        self,
        session_mgr: Optional[SessionManager] = None,
        schema_gen: Optional[SchemaGenerator] = None,
        content_ext: Optional[ContentExtractor] = None,
    ):
        """Initialize the orchestrator agent.

        Args:
            session_mgr: Session manager instance
            schema_gen: Schema generator instance
            content_ext: Content extractor instance
        """
        self.session_manager = session_mgr or session_manager
        self.schema_generator = schema_gen or schema_generator
        self.content_extractor = content_ext or content_extractor

    async def execute_scrape(
        self,
        request: ScrapeRequest,
        progress_callback: Optional[Callable[[str, Any], None]] = None,
    ) -> tuple[str, bool]:
        """Execute a scraping request.

        Args:
            request: The scraping request
            progress_callback: Optional callback for progress updates
                              callback(event_type: str, data: Any)

        Returns:
            Tuple of (session_id, success: bool)
        """
        # Initialize session
        session_id, metadata = await self.session_manager.initialize_session(request)

        try:
            # Send progress update
            self._send_progress(
                progress_callback,
                "session_created",
                {"session_id": session_id, "status": "pending"},
            )

            # Step 1: Update status to in_progress
            await self.session_manager.update_status(
                session_id, SessionStatus.IN_PROGRESS
            )
            self._send_progress(
                progress_callback, "status_update", {"status": "in_progress"}
            )

            # Step 2: Fetch URL content
            self._send_progress(progress_callback, "fetching_url", {"url": str(request.url)})
            html, error = await self._fetch_url(str(request.url))

            if error:
                await self._handle_error(session_id, f"Failed to fetch URL: {error}")
                self._send_progress(progress_callback, "error", {"message": error})
                return session_id, False

            self._send_progress(
                progress_callback, "url_fetched", {"content_length": len(html)}
            )

            # Step 3: Generate or use provided schema
            if request.extraction_schema:
                # Use provided schema
                schema = request.extraction_schema
                self._send_progress(
                    progress_callback, "schema_provided", {"schema": schema}
                )
            else:
                # Generate schema
                self._send_progress(progress_callback, "generating_schema", {})
                schema, error = await self.schema_generator.generate_schema(
                    request.purpose, html
                )

                if error:
                    await self._handle_error(
                        session_id, f"Failed to generate schema: {error}"
                    )
                    self._send_progress(progress_callback, "error", {"message": error})
                    return session_id, False

                self._send_progress(
                    progress_callback, "schema_generated", {"schema": schema}
                )

            # Save schema
            await self.session_manager.save_schema(session_id, schema)

            # Step 4: Extract content
            self._send_progress(progress_callback, "extracting_content", {})
            extracted_data, error = await self.content_extractor.extract_content(
                html, schema
            )

            if error:
                await self._handle_error(
                    session_id, f"Failed to extract content: {error}"
                )
                self._send_progress(progress_callback, "error", {"message": error})
                return session_id, False

            self._send_progress(
                progress_callback, "content_extracted", {"data": extracted_data}
            )

            # Step 5: Save results
            await self.session_manager.save_extracted_data(session_id, extracted_data)
            await self.session_manager.save_sources(session_id, [str(request.url)])

            # Step 6: Mark as completed
            await self.session_manager.update_status(session_id, SessionStatus.COMPLETED)
            self._send_progress(
                progress_callback,
                "completed",
                {"session_id": session_id, "data": extracted_data},
            )

            return session_id, True

        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Unexpected error: {str(e)}"
            await self._handle_error(session_id, error_msg)
            self._send_progress(progress_callback, "error", {"message": error_msg})
            return session_id, False

    async def _fetch_url(self, url: str) -> tuple[str, Optional[str]]:
        """Fetch URL content.

        Args:
            url: URL to fetch

        Returns:
            Tuple of (html_content, error_message)
        """
        async with HTTPClient() as client:
            return await client.fetch_url(url)

    async def _handle_error(self, session_id: str, error_message: str) -> None:
        """Handle error by updating session status.

        Args:
            session_id: The session identifier
            error_message: Error message
        """
        await self.session_manager.update_status(
            session_id, SessionStatus.FAILED, error_message
        )

    def _send_progress(
        self,
        callback: Optional[Callable[[str, Any], None]],
        event_type: str,
        data: Any,
    ) -> None:
        """Send progress update via callback.

        Args:
            callback: Progress callback function
            event_type: Type of event
            data: Event data
        """
        if callback:
            try:
                callback(event_type, data)
            except Exception:
                # Ignore callback errors to not disrupt workflow
                pass


# Global orchestrator instance
orchestrator = OrchestratorAgent()
