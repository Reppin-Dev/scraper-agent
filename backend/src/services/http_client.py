"""HTTP client service for fetching web pages."""
import httpx
from typing import Optional
from ..config import settings


class HTTPClient:
    """Async HTTP client for fetching web pages."""

    def __init__(self, timeout: Optional[int] = None):
        """Initialize the HTTP client.

        Args:
            timeout: Request timeout in seconds. Defaults to settings.default_timeout
        """
        self.timeout = timeout or settings.default_timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def fetch_url(
        self, url: str, max_retries: int = 3
    ) -> tuple[str, Optional[str]]:
        """Fetch HTML content from a URL.

        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts

        Returns:
            Tuple of (html_content, error_message)
            If successful, returns (html, None)
            If failed, returns ("", error_message)
        """
        if not self._client:
            raise RuntimeError("HTTPClient must be used as an async context manager")

        last_error = None

        for attempt in range(max_retries):
            try:
                response = await self._client.get(url)
                response.raise_for_status()
                return response.text, None

            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}: {e.response.reason_phrase}"
                # Don't retry on 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    break

            except httpx.TimeoutException:
                last_error = f"Request timed out after {self.timeout} seconds"

            except httpx.RequestError as e:
                last_error = f"Request failed: {str(e)}"

            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"

            # Wait a bit before retrying (exponential backoff)
            if attempt < max_retries - 1:
                import asyncio

                await asyncio.sleep(2**attempt)

        return "", last_error or "Unknown error occurred"


async def fetch_url(url: str) -> tuple[str, Optional[str]]:
    """Convenience function to fetch a URL.

    Args:
        url: URL to fetch

    Returns:
        Tuple of (html_content, error_message)
    """
    async with HTTPClient() as client:
        return await client.fetch_url(url)
