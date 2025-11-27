"""CLI tool for scraping websites with real-time progress tracking."""
import asyncio
import time
from typing import Optional
import httpx
import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

app = typer.Typer()
console = Console()


async def start_scrape(
    url: str,
    mode: str,
    purpose: str,
    api_url: str
) -> Optional[str]:
    """Initiate a scrape and return the session ID."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{api_url}/api/scrape",
                json={
                    "url": url,
                    "mode": mode,
                    "purpose": purpose
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("session_id")
        except httpx.HTTPStatusError as e:
            console.print(f"[red]Error starting scrape: {e.response.text}[/red]")
            return None
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return None


async def get_session_status(session_id: str, api_url: str) -> Optional[dict]:
    """Get the current status of a scraping session."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{api_url}/api/sessions/{session_id}")
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def create_status_display(session_data: dict, elapsed: float) -> Table:
    """Create a rich table displaying the current scrape status."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="cyan bold", no_wrap=True)
    table.add_column("Value", style="white")

    status = session_data.get("status", "unknown")
    pages_scraped = session_data.get("pages_scraped", 0)
    url = session_data.get("url", "")
    mode = session_data.get("mode", "")

    # Status with color
    status_colors = {
        "pending": "yellow",
        "in_progress": "blue",
        "completed": "green",
        "failed": "red"
    }
    status_color = status_colors.get(status, "white")

    table.add_row("Status", f"[{status_color}]{status.upper()}[/{status_color}]")
    table.add_row("URL", url)
    table.add_row("Mode", mode)
    table.add_row("Pages Scraped", str(pages_scraped))
    table.add_row("Elapsed Time", f"{elapsed:.1f}s")

    if status == "failed":
        error_msg = session_data.get("error_message", "Unknown error")
        table.add_row("Error", f"[red]{error_msg}[/red]")

    return table


async def track_scrape_progress(
    session_id: str,
    api_url: str,
    poll_interval: float = 1.0
) -> bool:
    """Track scraping progress with live updates."""
    start_time = time.time()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=False
    ) as progress:
        task = progress.add_task("[cyan]Initializing...", total=None)

        while True:
            elapsed = time.time() - start_time
            session_data = await get_session_status(session_id, api_url)

            if not session_data:
                progress.update(task, description="[red]Failed to get status")
                await asyncio.sleep(poll_interval)
                continue

            status = session_data.get("status", "unknown")
            pages_scraped = session_data.get("pages_scraped", 0)

            # Update progress description
            if status == "pending":
                progress.update(task, description="[yellow]Starting scrape...")
            elif status == "in_progress":
                progress.update(
                    task,
                    description=f"[cyan]Scraping... {pages_scraped} pages scraped"
                )
            elif status == "completed":
                duration = session_data.get("duration_seconds", elapsed)
                progress.update(
                    task,
                    description=f"[green]Completed! {pages_scraped} pages scraped in {duration:.1f}s"
                )
                progress.stop()

                # Show final summary
                console.print("\n")
                console.print(Panel(
                    create_status_display(session_data, duration),
                    title="[green]Scrape Complete",
                    border_style="green"
                ))

                # Show scraped URLs
                sources = session_data.get("sources", [])
                if sources:
                    console.print(f"\n[cyan]Scraped {len(sources)} URLs:[/cyan]")
                    for i, source in enumerate(sources[:10], 1):
                        console.print(f"  {i}. {source}")
                    if len(sources) > 10:
                        console.print(f"  ... and {len(sources) - 10} more")

                console.print(f"\n[cyan]Session ID:[/cyan] {session_id}")
                return True

            elif status == "failed":
                error_msg = session_data.get("error_message", "Unknown error")
                progress.update(task, description=f"[red]Failed: {error_msg}")
                progress.stop()

                console.print("\n")
                console.print(Panel(
                    create_status_display(session_data, elapsed),
                    title="[red]Scrape Failed",
                    border_style="red"
                ))
                return False

            await asyncio.sleep(poll_interval)


@app.command()
def scrape(
    url: str = typer.Argument(..., help="URL to scrape"),
    mode: str = typer.Option("whole-site", help="Scrape mode: 'single-page' or 'whole-site'"),
    purpose: str = typer.Option("General web scraping", help="Purpose of the scrape"),
    api_url: str = typer.Option("http://localhost:8000", help="API base URL"),
    poll_interval: float = typer.Option(1.0, help="Polling interval in seconds")
):
    """
    Scrape a website with real-time progress tracking.

    Examples:

        python -m src.cli.scrape https://example.com

        python -m src.cli.scrape https://example.com --mode single-page

        python -m src.cli.scrape https://example.com --purpose "Scrape gym information"
    """
    console.print(f"\n[bold cyan]Starting scrape of:[/bold cyan] {url}\n")

    async def run():
        # Start the scrape
        session_id = await start_scrape(url, mode, purpose, api_url)

        if not session_id:
            console.print("[red]Failed to start scrape[/red]")
            raise typer.Exit(1)

        console.print(f"[green]Session created:[/green] {session_id}\n")

        # Track progress
        success = await track_scrape_progress(session_id, api_url, poll_interval)

        if not success:
            raise typer.Exit(1)

    asyncio.run(run())


if __name__ == "__main__":
    app()
