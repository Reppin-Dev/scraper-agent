"""Request models for API endpoints."""
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, HttpUrl

from .session import ScrapeMode


class ScrapeRequest(BaseModel):
    """Request model for scraping endpoint."""

    url: HttpUrl = Field(..., description="URL to scrape")
    purpose: str = Field(
        ...,
        description="Purpose of scraping (e.g., 'Extract contact information')",
        min_length=1,
    )
    extraction_schema: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional predefined schema for extraction. If not provided, will be auto-generated.",
        alias="schema",
    )
    mode: ScrapeMode = Field(
        default=ScrapeMode.SINGLE_PAGE,
        description="Scraping mode: single-page or whole-site",
    )

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "purpose": "Extract contact information and business hours",
                "mode": "single-page",
            }
        }
