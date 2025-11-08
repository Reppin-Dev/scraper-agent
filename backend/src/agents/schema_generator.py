"""Schema generator subagent for creating extraction schemas."""
from typing import Optional

from .base import BaseSchemaGenerator


class SchemaGenerator(BaseSchemaGenerator):
    """Subagent for generating JSON schemas from purpose and HTML samples.

    Inherits all functionality from BaseSchemaGenerator.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the schema generator.

        Args:
            api_key: Anthropic API key. Defaults to settings.anthropic_api_key
        """
        super().__init__(api_key=api_key)


# Global schema generator instance
schema_generator = SchemaGenerator()
