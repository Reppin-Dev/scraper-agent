# BLOAT FILE - SAFE TO DELETE
# This file contains gym-specialized content extractor that has been deprecated.
# Import commented out in agents/specialized/__init__.py and is no longer used.
# Tests confirmed the application works without this file.
#
"""Gym-specialized content extractor."""
import json
from typing import Dict, Any, Optional

from ..base import BaseContentExtractor


class GymContentExtractor(BaseContentExtractor):
    """Content extractor specialized for gym and fitness facility websites.

    Extends BaseContentExtractor with gym-specific extraction strategies
    and enhanced prompts for thorough data collection.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the gym content extractor.

        Args:
            api_key: Anthropic API key. Defaults to settings.anthropic_api_key
        """
        super().__init__(api_key=api_key)

    def _build_url_extraction_prompt(self, url: str, schema_str: str) -> str:
        """Build gym-specific extraction prompt from URL.

        Args:
            url: URL to fetch
            schema_str: JSON string of the schema

        Returns:
            Formatted prompt string with gym-specific extraction guidance
        """
        return f"""Please fetch the GYM/FITNESS FACILITY webpage at {url} and extract ALL relevant data according to the provided schema.

Schema (defines what to extract):
```json
{schema_str}
```

IMPORTANT INSTRUCTIONS FOR GYM DATA EXTRACTION:

1. THOROUGHLY scan the ENTIRE webpage including:
   - Main hero section and headlines
   - Navigation menus (top nav, footer nav, mobile menus)
   - "About" / "Services" / "Amenities" sections
   - Class schedules and timetables
   - Pricing / Membership pages
   - Facility tour sections
   - Equipment lists
   - Footer information
   - Any modal popups or hidden content

2. For MODALITIES/PROGRAMS fields:
   - Check class schedule/timetable for ALL class types
   - Look in navigation menus under "Classes" or "Programs"
   - Scan "What We Offer" or "Services" sections
   - Check for both explicit names AND descriptions that match
   - Common synonyms to watch for:
     * "Cycling" = "Spin"
     * "Weight training" / "Resistance training" = "Strength training"
     * "Circuit training" = "Functional" or "HIIT"
     * "Core classes" = often includes "Pilates"
     * "Group fitness" = check what types are mentioned
   - Cross-reference EVERY option in the schema against the page
   - If a class/program exists on the site, include it!

3. For AMENITIES fields:
   - Check "Facilities" or "Amenities" sections thoroughly
   - Look at virtual tours or facility descriptions
   - Check footer and "What's Included" sections
   - Common synonyms:
     * "Change rooms" = "Lockers" + "Showers"
     * "Spa services" = "Massage" + "Sauna"
     * "Juice bar" / "Cafe" = "Smoothie bar"
     * "Treatment rooms" = "Massage" / "Physio" / "Therapy room"
   - Include amenities mentioned in membership benefits
   - Don't miss items in photo captions or image descriptions

4. For PRICING fields:
   - Check "Pricing", "Membership", "Join", or "Rates" pages/sections
   - Look for "Drop-in" rates vs "Membership" rates
   - Single class vs day pass pricing
   - May require clicking through to pricing pages

5. For each field:
   - Extract ALL matching data (be exhaustive, not selective)
   - For array fields with "Select from" options:
     * Treat this as a CHECKLIST - verify EACH option
     * Include an item if there's ANY evidence of it on the page
     * Better to be inclusive than miss items
   - Use exact data types specified in schema
   - Return null only if truly not found after thorough search

6. OUTPUT REQUIREMENTS:
   - Return ONLY valid JSON
   - No explanatory text before or after the JSON
   - Include all fields from schema (use null for not found)
   - For arrays, return ALL matching items found

Example extraction approach for modalities:
- Found "Yoga" in class schedule ✓
- Found "Pilates" in navigation menu ✓
- Found "Boxing" mentioned in facility tour ✓
- Checked for "HIIT" - found "High Intensity Training" ✓
- etc. (check EVERY option)

Extract the data now. Be COMPREHENSIVE and THOROUGH. Return ONLY the JSON object."""

    async def extract_content_from_url(
        self, url: str, schema: Dict[str, Any]
    ) -> tuple[Dict[str, Any], Optional[str]]:
        """Extract gym data from URL with increased token limit.

        Args:
            url: URL to fetch and extract from
            schema: Schema defining what data to extract

        Returns:
            Tuple of (extracted_data, error_message)
        """
        # Format schema for the prompt
        schema_str = json.dumps(schema, indent=2)

        prompt = self._build_url_extraction_prompt(url, schema_str)

        try:
            # Call Claude API with INCREASED max_tokens for thorough analysis
            message = self.client.messages.create(
                model=self.model,
                max_tokens=8192,  # Increased from 4096 for more thorough extraction
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

            # Parse the extracted data from the response
            extracted_data = self._extract_data(response_text)

            if extracted_data is None:
                return (
                    {},
                    "Failed to extract valid JSON data from Claude's response",
                )

            return extracted_data, None

        except Exception as e:
            return {}, f"Error extracting content: {str(e)}"


# Global gym content extractor instance
gym_content_extractor = GymContentExtractor()
