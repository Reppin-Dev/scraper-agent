"""Gym-specialized scraping API endpoints."""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Dict, Any

from ..models import ScrapeRequest, ScrapeResponse, SessionStatus
from ..utils.logger import logger

router = APIRouter(prefix="/api/scrape", tags=["gym"])


@router.post("/gym", response_model=ScrapeResponse)
async def create_gym_scrape_session(
    request: ScrapeRequest, background_tasks: BackgroundTasks
) -> ScrapeResponse:
    """Create a new gym scraping session using specialized gym agents.

    This endpoint uses gym-specialized agents that are optimized for extracting
    data from gym and fitness facility websites.

    Args:
        request: Scraping request with URL, purpose, optional schema, and mode
        background_tasks: FastAPI background tasks

    Returns:
        Scrape response with session ID and status
    """
    try:
        logger.info(f"Creating GYM scrape session for URL: {request.url}")

        # Create session immediately to get session_id
        from ..services import session_manager

        session_id, metadata = await session_manager.initialize_session(request)

        logger.info(f"Gym scrape session created: {session_id}")

        # Start the scraping process in the background with gym-specialized agents
        background_tasks.add_task(execute_gym_scrape_task, request, session_id)

        return ScrapeResponse(
            session_id=session_id,
            status=SessionStatus.PENDING,
            message="Gym scraping session created successfully. Processing with specialized gym agents in background.",
            websocket_url=f"ws://localhost:8000/ws/{session_id}",
        )

    except Exception as e:
        logger.error(f"Error creating gym scrape session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def execute_gym_scrape_task(request: ScrapeRequest, session_id: str) -> None:
    """Execute the gym scraping task in the background using specialized agents.

    Args:
        request: Scraping request
        session_id: Existing session ID to use
    """
    try:
        logger.info(f"Starting background GYM scrape task for {request.url} with session {session_id}")

        from ..services import session_manager
        from ..models import SessionStatus
        from ..agents.specialized.gym_schema_generator import gym_schema_generator
        from ..agents.specialized.gym_content_extractor import gym_content_extractor

        # Update status to in_progress
        await session_manager.update_status(session_id, SessionStatus.IN_PROGRESS)

        # Generate or use provided schema (with gym-specialized generator)
        if request.extraction_schema:
            schema = request.extraction_schema
            logger.info(f"Using provided schema for gym scraping: {session_id}")
        else:
            # Use GYM-SPECIALIZED schema generator
            logger.info(f"Generating gym-specialized schema for: {session_id}")
            schema, error = await gym_schema_generator.generate_schema_from_url(
                request.purpose, str(request.url)
            )
            if error:
                await session_manager.update_status(
                    session_id, SessionStatus.FAILED, f"Failed to generate gym schema: {error}"
                )
                logger.error(f"Gym scrape failed: {session_id} - {error}")
                return

        # Save schema
        await session_manager.save_schema(session_id, schema)
        logger.info(f"Schema saved for gym session: {session_id}")

        # Extract content using GYM-SPECIALIZED extractor
        logger.info(f"Extracting gym content with specialized agent: {session_id}")
        extracted_data, error = await gym_content_extractor.extract_content_from_url(
            str(request.url), schema
        )
        if error:
            await session_manager.update_status(
                session_id, SessionStatus.FAILED, f"Failed to extract gym content: {error}"
            )
            logger.error(f"Gym scrape failed: {session_id} - {error}")
            return

        # Save results
        await session_manager.save_extracted_data(session_id, extracted_data)
        await session_manager.save_sources(session_id, [str(request.url)])

        # Mark as completed
        await session_manager.update_status(session_id, SessionStatus.COMPLETED)
        logger.info(f"Gym scrape completed successfully: {session_id}")

    except Exception as e:
        logger.error(f"Error in background gym scrape task: {str(e)}")
        try:
            from ..services import session_manager
            from ..models import SessionStatus
            await session_manager.update_status(session_id, SessionStatus.FAILED, str(e))
        except:
            pass
