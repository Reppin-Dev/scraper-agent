"""Main orchestrator agent for coordinating the scraping workflow."""
import asyncio
from typing import Optional, Callable, Any, List, Dict
from urllib.parse import urlparse

from ..models import ScrapeRequest, SessionStatus, ScrapeMode
from ..config import settings
from ..services import SessionManager, session_manager, HTTPClient
from ..services.sitemap_discovery import SitemapDiscovery
from ..services.html_cleaner import html_cleaner

# Try to import BrowserClient for JS rendering, fallback to HTTPClient
try:
    from ..services.browser_client import BrowserClient
    HAS_BROWSER = True
except ImportError:
    HAS_BROWSER = False


class OrchestratorAgent:
    """Main agent that orchestrates Phase 1: sitemap-based raw HTML scraping."""

    def __init__(
        self,
        session_mgr: Optional[SessionManager] = None,
        sitemap_disco: Optional[SitemapDiscovery] = None,
    ):
        """Initialize the orchestrator agent.

        Args:
            session_mgr: Session manager instance
            sitemap_disco: Sitemap discovery instance
        """
        self.session_manager = session_mgr or session_manager
        self.sitemap_discovery = sitemap_disco or SitemapDiscovery()

    async def execute_scrape(
        self,
        request: ScrapeRequest,
        session_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, Any], None]] = None,
    ) -> tuple[str, bool]:
        """Execute Phase 1: Scraping with markdown conversion.

        This method:
        1. Discovers URLs based on mode:
           - SINGLE_PAGE: Uses only the provided URL
           - WHOLE_SITE: Discovers URLs from robots.txt → sitemaps
        2. Scrapes raw HTML from discovered URL(s)
        3. Converts HTML to markdown (NO Claude - using BeautifulSoup)
        4. Saves both raw HTML and markdown

        Phase 2 (chunking + embedding) and Phase 3 (query) are separate services.

        Args:
            request: The scraping request
            session_id: Optional pre-created session ID. If None, creates new session.
            progress_callback: Optional callback for progress updates
                              callback(event_type: str, data: Any)

        Returns:
            Tuple of (session_id, success: bool)
        """
        print("=== NEW ORCHESTRATOR CODE EXECUTING ===")
        # Initialize session (use provided session_id or create new one)
        if session_id:
            # Use pre-created session_id, initialize metadata for it
            metadata = self.session_manager.storage.load_metadata(session_id)
            if not metadata:
                # Create metadata for the provided session_id (don't generate new ID)
                _, metadata = await self.session_manager.initialize_session(request, session_id)
        else:
            # Create new session
            session_id, metadata = await self.session_manager.initialize_session(request)

        try:
            # Send progress update
            self._send_progress(
                progress_callback,
                "session_created",
                {"session_id": session_id, "status": "pending"},
            )

            # Update status to in_progress
            await self.session_manager.update_status(
                session_id, SessionStatus.IN_PROGRESS
            )
            self._send_progress(
                progress_callback, "status_update", {"status": "in_progress"}
            )

            # Step 1: Discover URLs (conditional based on mode)
            if request.mode == ScrapeMode.SINGLE_PAGE:
                # Single page mode: only scrape the exact URL provided
                urls = [str(request.url)]
                self._send_progress(
                    progress_callback,
                    "single_page_mode",
                    {"url": str(request.url), "message": "Single page mode - scraping only the specified URL"}
                )
            else:
                # Whole site mode: discover from robots.txt → sitemaps
                domain = self._extract_domain(str(request.url))
                self._send_progress(
                    progress_callback, "discovering_urls", {"domain": domain}
                )

                urls = await self.sitemap_discovery.discover_from_robots(domain)

                if not urls:
                    await self._handle_error(
                        session_id, "No URLs discovered from sitemaps"
                    )
                    self._send_progress(
                        progress_callback, "error", {"message": "No URLs found in sitemaps"}
                    )
                    return session_id, False

                self._send_progress(
                    progress_callback, "urls_discovered", {"count": len(urls), "urls": urls[:5]}
                )

            # Set total_pages in metadata after URL discovery
            await self.session_manager.update_progress(
                session_id, total_pages=len(urls), pages_scraped=0
            )

            # Step 2: Scrape raw HTML from all URLs (parallel with semaphore)
            pages_data = await self._fetch_urls_parallel(
                urls=urls,
                session_id=session_id,
                progress_callback=progress_callback,
                max_concurrent=settings.max_parallel_extractions
            )

            if not pages_data:
                await self._handle_error(
                    session_id, "Failed to scrape any pages"
                )
                self._send_progress(
                    progress_callback, "error", {"message": "No pages successfully scraped"}
                )
                return session_id, False

            # Step 3: Convert HTML to markdown
            self._send_progress(
                progress_callback, "converting_to_markdown", {"total_pages": len(pages_data)}
            )

            markdown_data = []
            for idx, page in enumerate(pages_data):
                self._send_progress(
                    progress_callback,
                    "converting_page",
                    {"url": page["page_url"], "progress": f"{idx + 1}/{len(pages_data)}"},
                )

                # Extract markdown sections from HTML
                sections = html_cleaner.extract_sections(page["raw_html"])

                # Combine all sections into single markdown content
                markdown_content = ""
                if sections:
                    markdown_content = "\n\n".join(section["content"] for section in sections)

                # Extract clean page name from URL path
                page_name = self._extract_page_name(page["page_url"])

                markdown_data.append({
                    "page_url": page["page_url"],
                    "page_name": page_name,
                    "markdown_content": markdown_content
                })

                self._send_progress(
                    progress_callback,
                    "page_converted",
                    {"url": page["page_url"], "markdown_length": len(markdown_content)},
                )

            # Step 4: Save both raw HTML and markdown to session directory
            await self.session_manager.save_raw_html(session_id, pages_data)
            await self.session_manager.save_markdown(session_id, markdown_data)
            await self.session_manager.save_sources(session_id, urls)

            # Mark as completed
            await self.session_manager.update_status(session_id, SessionStatus.COMPLETED)
            self._send_progress(
                progress_callback,
                "completed",
                {
                    "session_id": session_id,
                    "total_urls": len(urls),
                    "scraped_pages": len(pages_data),
                },
            )

            return session_id, True

        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Unexpected error: {str(e)}"
            await self._handle_error(session_id, error_msg)
            self._send_progress(progress_callback, "error", {"message": error_msg})
            return session_id, False

    async def _fetch_urls_parallel(
        self,
        urls: List[str],
        session_id: str,
        progress_callback: Optional[Callable[[str, Any], None]] = None,
        max_concurrent: int = 5
    ) -> List[Dict[str, str]]:
        """Fetch multiple URLs in parallel with concurrency control.

        Uses BrowserClient (Playwright) for JS rendering when available,
        falls back to HTTPClient for static HTML.

        Args:
            urls: List of URLs to fetch
            session_id: Session ID for progress tracking
            progress_callback: Optional progress callback
            max_concurrent: Maximum concurrent requests (default 5)

        Returns:
            List of successfully fetched pages with page_url and raw_html
        """
        results: List[Dict[str, str]] = []
        completed_count = 0
        lock = asyncio.Lock()

        if HAS_BROWSER:
            # Use BrowserClient for JS rendering (sequential due to browser resource sharing)
            print("[ORCHESTRATOR] Using BrowserClient (Playwright) for JS rendering")
            async with BrowserClient() as browser:
                for idx, url in enumerate(urls):
                    self._send_progress(
                        progress_callback,
                        "scraping_page",
                        {"url": url, "progress": f"{idx + 1}/{len(urls)}"},
                    )

                    html, error = await browser.render_page(url)

                    if error:
                        self._send_progress(
                            progress_callback,
                            "page_error",
                            {"url": url, "error": error},
                        )
                        continue

                    # Clean the HTML
                    html = browser.clean_html(html)

                    completed_count += 1
                    await self.session_manager.update_progress(
                        session_id, pages_scraped=completed_count
                    )

                    self._send_progress(
                        progress_callback,
                        "page_scraped",
                        {"url": url, "html_length": len(html)},
                    )

                    results.append({"page_url": url, "raw_html": html})
        else:
            # Fallback to HTTPClient (parallel, no JS rendering)
            print("[ORCHESTRATOR] Using HTTPClient (no JS rendering)")
            semaphore = asyncio.Semaphore(max_concurrent)

            async def fetch_one(url: str, idx: int) -> Optional[Dict[str, str]]:
                nonlocal completed_count
                async with semaphore:
                    self._send_progress(
                        progress_callback,
                        "scraping_page",
                        {"url": url, "progress": f"{idx + 1}/{len(urls)}"},
                    )

                    async with HTTPClient() as client:
                        html, error = await client.fetch_url(url)

                    if error:
                        self._send_progress(
                            progress_callback,
                            "page_error",
                            {"url": url, "error": error},
                        )
                        return None

                    # Update progress count
                    async with lock:
                        completed_count += 1
                        await self.session_manager.update_progress(
                            session_id, pages_scraped=completed_count
                        )

                    self._send_progress(
                        progress_callback,
                        "page_scraped",
                        {"url": url, "html_length": len(html)},
                    )

                    return {"page_url": url, "raw_html": html}

            # Create tasks for all URLs
            tasks = [fetch_one(url, idx) for idx, url in enumerate(urls)]

            # Execute in parallel with gather
            fetch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter successful results
            for result in fetch_results:
                if isinstance(result, dict) and result is not None:
                    results.append(result)
                elif isinstance(result, Exception):
                    print(f"[ORCHESTRATOR] Fetch error: {result}")

        return results

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL.

        Args:
            url: Full URL

        Returns:
            Domain (scheme + netloc)
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _extract_page_name(self, url: str) -> str:
        """Extract a clean page name from URL path.

        Args:
            url: Full URL

        Returns:
            Clean page name extracted from URL path
        """
        parsed = urlparse(url)
        path = parsed.path.strip('/')

        if not path:
            return "home"

        # Get the last path segment (without file extension)
        segments = path.split('/')
        last_segment = segments[-1]

        # Remove file extensions (.html, .php, etc.)
        if '.' in last_segment:
            last_segment = last_segment.rsplit('.', 1)[0]

        # If empty after removing extension, use second-to-last segment
        if not last_segment and len(segments) > 1:
            last_segment = segments[-2]

        # Convert URL-style to readable: "about-us" -> "about-us"
        # Keep hyphens as they make good page identifiers
        return last_segment or "home"

    async def _handle_error(self, session_id: str, error_message: str) -> None:
        """Handle error by updating session status.

        Args:
            session_id: The session identifier
            error_message: Error message
        """
        await self.session_manager.update_status(
            session_id, SessionStatus.FAILED, error_message
        )

    def _send_progress(
        self,
        callback: Optional[Callable[[str, Any], None]],
        event_type: str,
        data: Any,
    ) -> None:
        """Send progress update via callback.

        Args:
            callback: Progress callback function
            event_type: Type of event
            data: Event data
        """
        if callback:
            try:
                callback(event_type, data)
            except Exception:
                # Ignore callback errors to not disrupt workflow
                pass


# Global orchestrator instance
orchestrator = OrchestratorAgent()
