"""Specialized scraper agents for specific domains."""

from .gym_schema_generator import GymSchemaGenerator
from .gym_content_extractor import GymContentExtractor

__all__ = ["GymSchemaGenerator", "GymContentExtractor"]
