"""Gym-specialized schema generator."""
from typing import Optional

from ..base import BaseSchemaGenerator


class GymSchemaGenerator(BaseSchemaGenerator):
    """Schema generator specialized for gym and fitness facility websites.

    Extends BaseSchemaGenerator with gym-specific knowledge and field suggestions.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the gym schema generator.

        Args:
            api_key: Anthropic API key. Defaults to settings.anthropic_api_key
        """
        super().__init__(api_key=api_key)

    def _build_url_prompt(self, purpose: str, url: str) -> str:
        """Build gym-specific schema generation prompt from URL.

        Args:
            purpose: Description of what data to extract
            url: URL to fetch

        Returns:
            Formatted prompt string with gym-specific guidance
        """
        return f"""Please fetch the webpage at {url} and analyze its structure to create a JSON schema for extracting GYM/FITNESS FACILITY data.

Purpose: {purpose}

Based on the webpage content, generate a JSON schema that defines gym-specific fields such as:
- Facility name and type (gym, studio, fitness center)
- Pricing (memberships, day passes, class drop-ins)
- Access models (open gym, classes only, combination)
- Fitness modalities/programs offered (e.g., yoga, pilates, HIIT, strength training)
- Amenities and facilities (pools, saunas, lockers, etc.)
- Operating hours and special features
- Location and contact information

Field requirements:
1. Field names MUST be descriptive, snake_case
2. Field types: string, number, boolean, array, object
3. Descriptions should specify data format and content
4. Mark required vs optional fields appropriately

For categorical/enumerated fields (like modalities or amenities), include in the description:
"Select from: [option1, option2, option3, ...]" to indicate the allowed values.

Return ONLY a valid JSON object with this structure:
{{
  "fields": {{
    "field_name": {{
      "type": "string|number|boolean|array|object",
      "description": "What this field contains. For enums: Select from: [opt1, opt2, ...]",
      "required": true|false
    }}
  }}
}}

Example gym schema:
{{
  "fields": {{
    "gym_name": {{
      "type": "string",
      "description": "Official name of the gym or fitness facility",
      "required": true
    }},
    "day_pass_price": {{
      "type": "string",
      "description": "Price for a single day pass",
      "required": false
    }},
    "modalities": {{
      "type": "array",
      "description": "List of fitness modalities offered. Select from: Yoga, Pilates, HIIT, Strength training, Boxing, Spin, Swimming, Crossfit, etc.",
      "required": false
    }},
    "amenities": {{
      "type": "array",
      "description": "List of amenities available. Select from: Swimming pool, Sauna, Showers, Lockers, Massage, Towel service, etc.",
      "required": false
    }}
  }}
}}

Generate a comprehensive schema now for THIS gym website. Return ONLY the JSON, no other text."""


# Global gym schema generator instance
gym_schema_generator = GymSchemaGenerator()
