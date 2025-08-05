"""Display utilities for CODX."""

from typing import List, Dict
from rich.console import Console
from rich.table import Table
from rich.text import Text

console = Console()


def display_snippet_table(snippets: List[Dict], title: str = "Snippets") -> None:
    """Display snippets in a formatted table.
    
    Args:
        snippets: List of snippet dictionaries
        title: Table title
    """
    if not snippets:
        console.print("[yellow]No snippets found.[/yellow]")
        return
    
    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Description", style="green")
    table.add_column("Language", style="yellow", no_wrap=True)
    table.add_column("Tags", style="blue")
    table.add_column("Content Preview", style="white")
    
    for snippet in snippets:
        # Truncate content for preview
        content_preview = snippet.get('content', '')[:50]
        if len(snippet.get('content', '')) > 50:
            content_preview += "..."
        
        # Format tags
        tags = ', '.join(snippet.get('tags', []))
        if not tags:
            tags = "[dim]none[/dim]"
        
        table.add_row(
            str(snippet.get('id', 'N/A')),
            snippet.get('description', 'No description'),
            snippet.get('language', 'text'),
            tags,
            content_preview.replace('\n', ' ')
        )
    
    console.print(table)
    console.print(f"\n[dim]Total: {len(snippets)} snippet(s)[/dim]")