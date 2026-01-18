#!/usr/bin/env python3
"""CLI tool to embed cleaned markdown sites into Milvus vector database with progress tracking.

Examples:
    # List available files
    python -m src.cli.embed_sites list

    # Embed all cleaned markdown files
    python -m src.cli.embed_sites embed

    # Embed a specific file
    python -m src.cli.embed_sites embed --file example.com__20251124_001545.json

    # Recreate collection and embed all
    python -m src.cli.embed_sites embed --recreate

    # Delete entire collection (with confirmation)
    python -m src.cli.embed_sites delete

    # Delete entire collection (skip confirmation)
    python -m src.cli.embed_sites delete --force

    # Delete specific domain data
    python -m src.cli.embed_sites delete --domain example.com

    # Delete specific domain (skip confirmation)
    python -m src.cli.embed_sites delete --domain example.com --force
"""
import time
from typing import Optional, List
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table

from ..services import storage_service, vector_service
from ..utils.logger import logger

app = typer.Typer()
console = Console()


def list_files_table():
    """Display available files in a nice table."""
    files = storage_service.list_raw_html_files()

    if not files:
        console.print("[yellow]No cleaned markdown files found.[/yellow]")
        return []

    table = Table(title=f"Available Cleaned Markdown Files ({len(files)})")
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("Filename", style="white")
    table.add_column("Site", style="green")  # DEPRECATED: was "Gym/Site"
    table.add_column("Pages", style="yellow", justify="right")

    for i, filename in enumerate(files, 1):
        data = storage_service.load_raw_html(filename)
        if data:
            site_name = data.get("site_name", "Unknown")  # DEPRECATED: was gym_name = data.get("gym_name", "Unknown")
            page_count = str(len(data.get("pages", [])))
            table.add_row(str(i), filename, site_name, page_count)  # DEPRECATED: was gym_name
        else:
            table.add_row(str(i), filename, "[red]Failed to load[/red]", "-")

    console.print(table)
    return files


def embed_file_with_progress(
    filename: str,
    progress: Optional[Progress] = None,
    file_task: Optional[int] = None,
    page_task: Optional[int] = None,
    chunk_task: Optional[int] = None
) -> tuple[bool, int]:
    """Embed a single file with progress tracking.

    Args:
        filename: Name of the file to embed
        progress: Single Progress object for all progress bars
        file_task: Task ID for file-level progress
        page_task: Task ID for page-level progress
        chunk_task: Task ID for chunk-level progress

    Returns:
        Tuple of (success: bool, total_chunks: int)
    """
    # Load cleaned markdown data
    data = storage_service.load_raw_html(filename)
    if not data:
        logger.error(f"Failed to load file: {filename}")
        return False, 0

    domain = data.get("website", "unknown")
    site_name = data.get("site_name", "Unknown Site")  # DEPRECATED: was gym_name = data.get("gym_name", "Unknown Gym")
    pages = data.get("pages", [])

    if not pages:
        logger.warning(f"No pages found in {filename}")
        return False, 0

    # Update page progress bar
    if progress and page_task is not None:
        progress.update(page_task, total=len(pages), completed=0)

    # Initialize vector service
    vector_service.create_collection()

    # Process each page
    total_chunks = 0
    for page_idx, page in enumerate(pages):
        page_name = page.get("page_name", "Unknown Page")
        page_url = page.get("page_url", "")
        markdown_content = page.get("markdown_content", "")

        if not markdown_content:
            logger.warning(f"Skipping empty page: {page_name}")
            if progress and page_task is not None:
                progress.advance(page_task)
            continue

        # Chunk the markdown
        chunks = vector_service.chunk_markdown(markdown_content, page_name)

        if not chunks:
            logger.warning(f"No chunks extracted from {page_name}")
            if progress and page_task is not None:
                progress.advance(page_task)
            continue

        # Update chunk progress bar
        if progress and chunk_task is not None:
            progress.update(chunk_task, total=len(chunks), completed=0)

        # Define progress callback for chunk embedding
        def chunk_callback(current: int, total: int):
            if progress and chunk_task is not None:
                progress.update(chunk_task, completed=current)

        # Insert chunks into Milvus with progress tracking
        vector_service.insert_chunks(
            domain=domain,
            site_name=site_name,  # DEPRECATED: was gym_name=gym_name
            page_name=page_name,
            page_url=page_url,
            chunks=chunks,
            progress_callback=chunk_callback
        )

        total_chunks += len(chunks)

        # Advance page progress
        if progress and page_task is not None:
            progress.advance(page_task)

    # Advance file progress
    if progress and file_task is not None:
        progress.advance(file_task)

    return True, total_chunks


@app.command(name="list")
def list_command():
    """List all available cleaned markdown files."""
    list_files_table()


@app.command()
def delete(
    domain: Optional[str] = typer.Option(None, "--domain", help="Delete specific domain only"),
    force: bool = typer.Option(False, "--force", is_flag=True, help="Skip confirmation prompt")
):
    """
    Delete the Milvus collection or specific domain data.

    By default, deletes the entire collection. Use --domain to delete specific domain data.
    """
    from pymilvus import utility, Collection

    # Connect to Milvus
    vector_service._connect()

    if domain:
        # Delete specific domain
        if not force:
            confirm = typer.confirm(f"Are you sure you want to delete all data for domain '{domain}'?")
            if not confirm:
                console.print("[yellow]Deletion cancelled[/yellow]")
                return

        if not utility.has_collection(vector_service.collection_name):
            console.print(f"[red]Collection '{vector_service.collection_name}' does not exist[/red]")
            return

        console.print(f"[yellow]Deleting data for domain: {domain}[/yellow]")
        vector_service.collection = Collection(vector_service.collection_name)
        vector_service.delete_by_domain(domain)
        console.print(f"[green]✓ Deleted all data for domain '{domain}'[/green]")
    else:
        # Delete entire collection
        if not force:
            confirm = typer.confirm(f"Are you sure you want to delete the entire collection '{vector_service.collection_name}'?")
            if not confirm:
                console.print("[yellow]Deletion cancelled[/yellow]")
                return

        if not utility.has_collection(vector_service.collection_name):
            console.print(f"[yellow]Collection '{vector_service.collection_name}' does not exist[/yellow]")
            return

        console.print(f"[yellow]Deleting collection: {vector_service.collection_name}[/yellow]")
        Collection(vector_service.collection_name).drop()
        console.print(f"[green]✓ Collection '{vector_service.collection_name}' deleted successfully[/green]")


@app.command()
def embed(
    file: Optional[str] = typer.Option(None, "--file", help="Specific file to embed"),
    recreate: bool = typer.Option(False, "--recreate", is_flag=True, help="Recreate Milvus collection")
):
    """
    Embed cleaned markdown files into Milvus vector database.

    By default, embeds all available files. Use --file to embed a specific file.
    """
    # Recreate collection if requested
    if recreate:
        console.print("[yellow]⚠ Recreating Milvus collection (all existing data will be lost)[/yellow]")
        from pymilvus import utility, Collection
        vector_service._connect()
        if utility.has_collection(vector_service.collection_name):
            Collection(vector_service.collection_name).drop()
            console.print("[green]✓ Dropped existing collection[/green]")

    # Get files to embed
    if file:
        files = [file]
        console.print(f"\n[bold cyan]Embedding file:[/bold cyan] {file}\n")
    else:
        files = storage_service.list_raw_html_files()
        if not files:
            console.print("[red]No cleaned markdown files found to embed[/red]")
            raise typer.Exit(1)
        console.print(f"\n[bold cyan]Embedding {len(files)} files...[/bold cyan]\n")

    # Load model (no spinner to avoid conflicts with Progress bars)
    console.print("[bold green]Loading BGE-M3 embedding model...[/bold green]")
    vector_service.load_model()
    console.print("[green]✓ Model loaded successfully[/green]\n")

    # Create single progress bar with multiple tasks
    start_time = time.time()
    success_count = 0
    total_chunks = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        console=console,
        transient=False
    ) as progress:

        # Create progress tasks (all in the same Progress instance)
        file_task = progress.add_task("[cyan]Files...", total=len(files))
        page_task = progress.add_task("  [cyan]Pages:", total=0)
        chunk_task = progress.add_task("  [green]Chunks:", total=0)

        # Process each file
        for filename in files:
            progress.update(
                file_task,
                description=f"[cyan]Processing {filename[:50]}..."
            )

            try:
                success, chunks = embed_file_with_progress(
                    filename,
                    progress, file_task,
                    page_task,
                    chunk_task
                )

                if success:
                    success_count += 1
                    total_chunks += chunks

            except Exception as e:
                logger.error(f"Failed to embed {filename}: {e}")
                console.print(f"[red]✗ Failed: {filename}[/red]")
                continue

    # Calculate duration
    duration = time.time() - start_time

    # Show final summary
    console.print("\n")

    summary = Table(show_header=False, box=None, padding=(0, 2))
    summary.add_column("Field", style="cyan bold")
    summary.add_column("Value", style="white")

    summary.add_row("Files Processed", f"{success_count}/{len(files)}")
    summary.add_row("Total Chunks", str(total_chunks))
    summary.add_row("Duration", f"{duration:.1f}s")

    if success_count == len(files):
        summary.add_row("Status", "[green]All files embedded successfully[/green]")
        title_style = "green"
        title = "Embedding Complete"
    else:
        summary.add_row("Status", f"[yellow]{len(files) - success_count} files failed[/yellow]")
        title_style = "yellow"
        title = "Embedding Completed with Errors"

    console.print(Panel(
        summary,
        title=f"[{title_style}]{title}[/{title_style}]",
        border_style=title_style
    ))

    if success_count < len(files):
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
