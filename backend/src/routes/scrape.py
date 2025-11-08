"""Scraping API endpoints."""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Dict, Any

from ..models import ScrapeRequest, ScrapeResponse, SessionStatus
from ..agents import orchestrator
from ..utils.logger import logger

router = APIRouter(prefix="/api", tags=["scrape"])


@router.post("/scrape", response_model=ScrapeResponse)
async def create_scrape_session(
    request: ScrapeRequest, background_tasks: BackgroundTasks
) -> ScrapeResponse:
    """Create a new scraping session.

    Args:
        request: Scraping request with URL, purpose, optional schema, and mode
        background_tasks: FastAPI background tasks

    Returns:
        Scrape response with session ID and status
    """
    try:
        logger.info(f"Creating scrape session for URL: {request.url}")

        # Create session immediately to get session_id
        from ..services import session_manager

        session_id, metadata = await session_manager.initialize_session(request)

        logger.info(f"Session created: {session_id}")

        # Start the scraping process in the background with the session_id
        background_tasks.add_task(execute_scrape_task, request, session_id)

        return ScrapeResponse(
            session_id=session_id,
            status=SessionStatus.PENDING,
            message="Scraping session created successfully. Processing in background.",
            websocket_url=f"ws://localhost:8000/ws/{session_id}",
        )

    except Exception as e:
        logger.error(f"Error creating scrape session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def execute_scrape_task(request: ScrapeRequest, session_id: str) -> None:
    """Execute the scraping task in the background.

    Args:
        request: Scraping request
        session_id: Existing session ID to use
    """
    try:
        logger.info(f"Starting background scrape task for {request.url} with session {session_id}")

        from ..services import session_manager
        from ..models import SessionStatus

        # Update status to in_progress
        await session_manager.update_status(session_id, SessionStatus.IN_PROGRESS)

        # Generate or use provided schema
        from ..agents import schema_generator, content_extractor

        if request.extraction_schema:
            schema = request.extraction_schema
        else:
            # Let Claude fetch the URL and generate schema
            schema, error = await schema_generator.generate_schema_from_url(request.purpose, str(request.url))
            if error:
                await session_manager.update_status(session_id, SessionStatus.FAILED, f"Failed to generate schema: {error}")
                logger.error(f"Scrape failed: {session_id} - {error}")
                return

        # Save schema
        await session_manager.save_schema(session_id, schema)

        # Extract content - Let Claude fetch the URL and extract
        extracted_data, error = await content_extractor.extract_content_from_url(str(request.url), schema)
        if error:
            await session_manager.update_status(session_id, SessionStatus.FAILED, f"Failed to extract content: {error}")
            logger.error(f"Scrape failed: {session_id} - {error}")
            return

        # Save results
        await session_manager.save_extracted_data(session_id, extracted_data)
        await session_manager.save_sources(session_id, [str(request.url)])

        # Mark as completed
        await session_manager.update_status(session_id, SessionStatus.COMPLETED)
        logger.info(f"Scrape completed successfully: {session_id}")

    except Exception as e:
        logger.error(f"Error in background scrape task: {str(e)}")
        try:
            from ..services import session_manager
            from ..models import SessionStatus
            await session_manager.update_status(session_id, SessionStatus.FAILED, str(e))
        except:
            pass
