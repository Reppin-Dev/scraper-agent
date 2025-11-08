"""Content extractor subagent for extracting data from HTML."""
from typing import Optional

from .base import BaseContentExtractor


class ContentExtractor(BaseContentExtractor):
    """Subagent for extracting structured data from HTML using a schema.

    Inherits all functionality from BaseContentExtractor.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the content extractor.

        Args:
            api_key: Anthropic API key. Defaults to settings.anthropic_api_key
        """
        super().__init__(api_key=api_key)


# Global content extractor instance
content_extractor = ContentExtractor()
