"""Base schema generator class for creating extraction schemas."""
import json
from typing import Dict, Any, Optional
from anthropic import Anthropic

from ...config import settings


class BaseSchemaGenerator:
    """Base class for generating JSON schemas from purpose and HTML samples."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-5-20250929"):
        """Initialize the schema generator.

        Args:
            api_key: Anthropic API key. Defaults to settings.anthropic_api_key
            model: Claude model to use
        """
        self.client = Anthropic(api_key=api_key or settings.anthropic_api_key)
        self.model = model

    async def generate_schema_from_url(
        self, purpose: str, url: str
    ) -> tuple[Dict[str, Any], Optional[str]]:
        """Generate a JSON schema for data extraction by fetching the URL.

        Args:
            purpose: Description of what data to extract
            url: URL to fetch and analyze

        Returns:
            Tuple of (schema_dict, error_message)
            If successful, returns (schema, None)
            If failed, returns ({}, error_message)
        """
        prompt = self._build_url_prompt(purpose, url)

        try:
            # Call Claude API with web fetch tool
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
                tools=[{
                    "type": "web_fetch_20250910",
                    "name": "web_fetch",
                    "max_uses": 3
                }],
                extra_headers={"anthropic-beta": "web-fetch-2025-09-10"}
            )

            # Extract the response text from all text content blocks
            response_text = ""
            for block in message.content:
                if hasattr(block, 'text') and block.text:
                    response_text += block.text

            # Parse the JSON schema from the response
            schema = self._extract_schema(response_text)

            if not schema:
                return {}, "Failed to extract valid JSON schema from Claude's response"

            return schema, None

        except Exception as e:
            return {}, f"Error generating schema: {str(e)}"

    async def generate_schema(
        self, purpose: str, html_sample: str, max_length: int = 5000
    ) -> tuple[Dict[str, Any], Optional[str]]:
        """Generate a JSON schema for data extraction.

        Args:
            purpose: Description of what data to extract
            html_sample: Sample HTML content to analyze
            max_length: Maximum length of HTML to send to Claude (to avoid token limits)

        Returns:
            Tuple of (schema_dict, error_message)
            If successful, returns (schema, None)
            If failed, returns ({}, error_message)
        """
        # Truncate HTML if too long
        if len(html_sample) > max_length:
            html_sample = html_sample[:max_length] + "\n... (truncated)"

        # Build the prompt
        prompt = self._build_html_prompt(purpose, html_sample)

        try:
            # Call Claude API with web fetch tool
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
                tools=[{
                    "type": "web_fetch_20250910",
                    "name": "web_fetch",
                    "max_uses": 3
                }],
                extra_headers={"anthropic-beta": "web-fetch-2025-09-10"}
            )

            # Extract the response text
            response_text = message.content[0].text

            # Parse the JSON schema from the response
            schema = self._extract_schema(response_text)

            if not schema:
                return {}, "Failed to extract valid JSON schema from Claude's response"

            return schema, None

        except Exception as e:
            return {}, f"Error generating schema: {str(e)}"

    def _build_url_prompt(self, purpose: str, url: str) -> str:
        """Build the prompt for schema generation from URL.

        Args:
            purpose: Description of what data to extract
            url: URL to fetch

        Returns:
            Formatted prompt string
        """
        return f"""Please fetch the webpage at {url} and analyze its structure to create a JSON schema for data extraction.

Purpose: {purpose}

Based on the webpage content, generate a JSON schema that defines:
1. Field names (descriptive, snake_case)
2. Field types (string, number, boolean, array, object)
3. Brief descriptions of what each field should contain
4. Whether fields are required or optional

Return ONLY a valid JSON object with this structure:
{{
  "fields": {{
    "field_name": {{
      "type": "string|number|boolean|array|object",
      "description": "What this field contains",
      "required": true|false
    }}
  }}
}}

Example output:
{{
  "fields": {{
    "company_name": {{
      "type": "string",
      "description": "Name of the company",
      "required": true
    }},
    "contact_email": {{
      "type": "string",
      "description": "Primary contact email address",
      "required": false
    }}
  }}
}}

Generate the schema now. Return ONLY the JSON, no other text."""

    def _build_html_prompt(self, purpose: str, html_sample: str) -> str:
        """Build the prompt for schema generation from HTML.

        Args:
            purpose: Description of what data to extract
            html_sample: Sample HTML content

        Returns:
            Formatted prompt string
        """
        return f"""You are a schema generation expert. Your task is to analyze HTML content and create a JSON schema that defines what data should be extracted based on the given purpose.

Purpose: {purpose}

HTML Sample:
```html
{html_sample}
```

Based on the purpose and the HTML structure, generate a JSON schema that defines:
1. Field names (descriptive, snake_case)
2. Field types (string, number, boolean, array, object)
3. Brief descriptions of what each field should contain
4. Whether fields are required or optional

Return ONLY a valid JSON object with this structure:
{{
  "fields": {{
    "field_name": {{
      "type": "string|number|boolean|array|object",
      "description": "What this field contains",
      "required": true|false
    }}
  }}
}}

Example output:
{{
  "fields": {{
    "company_name": {{
      "type": "string",
      "description": "Name of the company",
      "required": true
    }},
    "contact_email": {{
      "type": "string",
      "description": "Primary contact email address",
      "required": false
    }},
    "phone_numbers": {{
      "type": "array",
      "description": "List of phone numbers",
      "required": false
    }}
  }}
}}

Generate the schema now. Return ONLY the JSON, no other text."""

    def _extract_schema(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Extract and validate JSON schema from Claude's response.

        Args:
            response_text: Raw response from Claude

        Returns:
            Parsed schema dict or None if invalid
        """
        try:
            # Try to find JSON in the response
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1

            if start_idx == -1 or end_idx == 0:
                return None

            json_str = response_text[start_idx:end_idx]
            schema = json.loads(json_str)

            # Validate schema structure
            if "fields" not in schema:
                return None

            return schema

        except json.JSONDecodeError:
            return None
        except Exception:
            return None
