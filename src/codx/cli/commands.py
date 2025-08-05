"""CLI commands for codx."""

import typer
from typing import Optional, List
import os
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.text import Text
from rich.markdown import Markdown
import pyperclip

from ..core.database import Database
from ..core.models import Snippet
from ..utils.variables import extract_variables, prompt_for_variables
from ..utils.execution import execute_snippet, open_editor_for_content, get_file_extension
import json
from ..utils.search import search_snippets
from ..tui import SnippetFinderApp

console = Console()

# Create the typer app instance
app = typer.Typer(help="CODX - A powerful code snippet manager")

def get_db_path():
    """Get the default database path."""
    home_dir = Path.home()
    codx_dir = home_dir / ".codx"
    codx_dir.mkdir(exist_ok=True)
    return str(codx_dir / "codx.db")

def ensure_database_exists():
    """Ensure the database file exists."""
    db_path = get_db_path()
    if not Path(db_path).exists():
        console.print("[red]Database not found. Please run 'codx init' first.[/red]")
        raise typer.Exit(1)

def _display_snippet_details(snippet: dict):
    """Display detailed information about a snippet."""
    # Create details panel
    details = f"ID: {snippet['id']}\n"
    details += f"Description: {snippet['description']}\n"
    details += f"Language: {snippet['language'] or 'None'}\n"
    details += f"Tags: {', '.join(snippet['tags']) if snippet['tags'] else 'None'}\n"
    if 'created_at' in snippet:
        details += f"Created: {snippet['created_at']}"
    
    console.print(Panel(details, title="Snippet Details", border_style="blue"))
    
    # Display code with syntax highlighting
    if snippet['language']:
        syntax = Syntax(snippet['content'], snippet['language'], theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title="Content", border_style="green"))
    else:
        console.print(Panel(snippet['content'], title="Content", border_style="green"))
    
    # Check for variables
    variables = extract_variables(snippet['content'])
    if variables:
        console.print(f"\n[cyan]Variables detected: {', '.join(variables)}[/cyan]")

@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="Force initialization without confirmation")
):
    """Initialize the codx database."""
    db_path = get_db_path()
    
    if Path(db_path).exists():
        # Enhanced confirmation for destructive operation
        console.print(f"[yellow]⚠️  Warning: Database '{db_path}' already exists.[/yellow]")
        
        # Count existing snippets to show user what they'll lose
        try:
            existing_db = Database(db_path)
            snippets = existing_db.get_all_snippets()
            snippet_count = len(snippets)
            existing_db.close()
            
            if snippet_count > 0:
                console.print(f"[red]This will permanently delete {snippet_count} existing snippet(s)![/red]")
                console.print("[dim]Consider backing up your database before proceeding.[/dim]")
        except Exception:
            console.print("[yellow]Unable to read existing database.[/yellow]")
        
        if not force:
            console.print("\n[bold]This action cannot be undone![/bold]")
            if not Confirm.ask("Are you sure you want to recreate the database?", default=False):
                console.print("[yellow]Database initialization cancelled.[/yellow]")
                raise typer.Exit(0)
        
        try:
            os.remove(db_path)
            console.print("[yellow]Existing database removed.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error removing existing database: {e}[/red]")
            raise typer.Exit(1)
    
    db = Database(db_path)
    try:
        db.initialize_database()
        # Populate FTS5 table if there are existing snippets
        db.populate_fts_table()
        console.print("[green]✓ Database initialized successfully![/green]")
        console.print("[dim]You can now add snippets with 'codx add'[/dim]")
    except Exception as e:
        console.print(f"[red]Error initializing database: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()

@app.command()
def export(
    output_file: str = typer.Argument(..., help="Output file path for export")
):
    """Export all snippets to a JSON file."""
    ensure_database_exists()
    
    db = Database(get_db_path())
    try:
        snippets = db.get_all_snippets()
        
        if not snippets:
            console.print("[yellow]No snippets found to export.[/yellow]")
            raise typer.Exit(0)
        
        # Prepare export data
        export_data = {
            "version": "1.0",
            "exported_at": str(Path().cwd()),
            "snippets": snippets
        }
        
        # Write to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        console.print(f"[green]✓ {len(snippets)} snippets exported to {output_file}![/green]")
        
    except typer.Exit:
        raise  # Re-raise typer.Exit without modification
    except Exception as e:
        console.print(f"[red]Error exporting snippets: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()

@app.command(name="import")
def import_snippets(
    input_file: str = typer.Argument(..., help="Input file path for import")
):
    """Import snippets from a JSON file."""
    ensure_database_exists()
    
    input_path = Path(input_file)
    if not input_path.exists():
        console.print(f"[red]Input file {input_file} not found.[/red]")
        raise typer.Exit(1)
    
    db = Database(get_db_path())
    try:
        # Read import file
        with open(input_path, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        # Validate import data
        if 'snippets' not in import_data:
            console.print("[red]Invalid import file format. Missing 'snippets' key.[/red]")
            raise typer.Exit(1)
        
        snippets = import_data['snippets']
        if not isinstance(snippets, list):
            console.print("[red]Invalid import file format. 'snippets' must be a list.[/red]")
            raise typer.Exit(1)
        
        if not snippets:
            console.print("[yellow]No snippets found in import file.[/yellow]")
            raise typer.Exit(0)
        
        # Import snippets
        imported_count = 0
        for snippet in snippets:
            try:
                # Validate required fields
                if 'description' not in snippet or 'content' not in snippet:
                    console.print(f"[yellow]Skipping invalid snippet: missing required fields[/yellow]")
                    continue
                
                # Add snippet to database
                snippet_id = db.add_snippet(
                    description=snippet['description'],
                    content=snippet['content'],
                    language=snippet.get('language'),
                    tags=snippet.get('tags', [])
                )
                imported_count += 1
                
            except Exception as e:
                console.print(f"[yellow]Skipping snippet '{snippet.get('description', 'Unknown')}': {e}[/yellow]")
                continue
        
        console.print(f"[green]✓ {imported_count} snippets imported successfully![/green]")
        
        if imported_count < len(snippets):
            skipped = len(snippets) - imported_count
            console.print(f"[yellow]{skipped} snippets were skipped due to errors.[/yellow]")
        
    except typer.Exit:
        raise  # Re-raise typer.Exit without modification
    except json.JSONDecodeError:
        console.print("[red]Invalid JSON file format.[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error importing snippets: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()

@app.command()
def delete(
    snippet_id: int = typer.Argument(..., help="ID of the snippet to delete")
):
    """Delete a code snippet."""
    ensure_database_exists()
    
    db = Database(get_db_path())
    try:
        snippet = db.get_snippet_by_id(snippet_id)
        
        if not snippet:
            console.print(f"[red]Snippet with ID {snippet_id} not found.[/red]")
            raise typer.Exit(1)
        
        # Display snippet details
        _display_snippet_details(snippet)
        
        # Confirm deletion
        if not Confirm.ask(f"\nAre you sure you want to delete snippet '{snippet['description']}'?"):
            console.print("[yellow]Deletion cancelled.[/yellow]")
            raise typer.Exit(0)
        
        # Delete the snippet
        success = db.delete_snippet(snippet_id)
        
        if success:
            console.print(f"[green]Snippet deleted successfully![/green]")
        else:
            console.print(f"[red]Failed to delete snippet {snippet_id}.[/red]")
            raise typer.Exit(1)
        
    except typer.Exit:
        raise  # Re-raise typer.Exit without modification
    except Exception as e:
        console.print(f"[red]Error deleting snippet: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()

@app.command()
def add(
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Read content from file"),
    content: Optional[str] = typer.Option(None, "--content", "-c", help="Snippet content"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Snippet description"),
    language: Optional[str] = typer.Option(None, "--language", "-l", help="Programming language"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags")
):
    """Add a new code snippet."""
    ensure_database_exists()
    
    try:
        # Get content
        if file:
            file_path = Path(file)
            if not file_path.exists():
                console.print(f"[red]File '{file}' not found.[/red]")
                raise typer.Exit(1)
            
            content = file_path.read_text(encoding='utf-8')
            
            # Infer language from file extension if not provided
            if not language:
                extension = file_path.suffix.lower()
                language_map = {
                    '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                    '.java': 'java', '.cpp': 'cpp', '.c': 'c', '.cs': 'csharp',
                    '.php': 'php', '.rb': 'ruby', '.go': 'go', '.rs': 'rust',
                    '.sh': 'bash', '.sql': 'sql', '.html': 'html', '.css': 'css',
                    '.json': 'json', '.xml': 'xml', '.yaml': 'yaml', '.yml': 'yaml'
                }
                language = language_map.get(extension)
        elif content:
            # Content provided via --content option
            pass  # content is already set
        else:
            # Interactive content input
            console.print("\n[yellow]Enter your code snippet (press Ctrl+D when finished):[/yellow]")
            console.print("[dim]Tip: You can also use --file to read from a file[/dim]")
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                content = "\n".join(lines)
            except KeyboardInterrupt:
                console.print("\n[yellow]Operation cancelled by user.[/yellow]")
                raise typer.Exit(0)
        
        # Validate content
        if not content or not content.strip():
            console.print("[red]Error: Snippet content cannot be empty.[/red]")
            raise typer.Exit(1)
        
        if len(content) > 10000:  # 10KB limit
            console.print("[red]Error: Snippet content is too large (max 10KB).[/red]")
            raise typer.Exit(1)
        
        # Get description
        if not description:
            description = Prompt.ask("Enter a description for this snippet")
        
        if not description or not description.strip():
            console.print("[red]Error: Description cannot be empty.[/red]")
            raise typer.Exit(1)
        
        if len(description) > 200:
            console.print("[red]Error: Description is too long (max 200 characters).[/red]")
            raise typer.Exit(1)
        
        # Get language
        if not language:
            language = Prompt.ask("Enter programming language (optional)", default="")
        
        # Get tags
        if not tags:
            tags = Prompt.ask("Enter tags (comma-separated, optional)", default="")
        
        # Parse tags
        tag_list = []
        if tags and tags.strip():
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # Show preview
        console.print("\n[bold]Preview:[/bold]")
        
        preview_content = f"Description: {description}\n"
        preview_content += f"Language: {language or 'None'}\n"
        preview_content += f"Tags: {', '.join(tag_list) if tag_list else 'None'}"
        
        console.print(Panel(preview_content, title="Details", border_style="blue"))
        
        # Show code with syntax highlighting
        if language:
            syntax = Syntax(content, language, theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title="Content", border_style="green"))
        else:
            console.print(Panel(content, title="Content", border_style="green"))
        
        # Check for variables
        variables = extract_variables(content)
        if variables:
            console.print(f"\n[cyan]Variables detected: {', '.join(variables)}[/cyan]")
        
        # Confirm save
        if not Confirm.ask("\nSave this snippet?"):
            console.print("[yellow]Snippet not saved.[/yellow]")
            raise typer.Exit(0)
        
        # Save to database
        db = Database(get_db_path())
        try:
            snippet_id = db.add_snippet(
                description=description,
                content=content,
                language=language if language else None,
                tags=tag_list
            )
            console.print(f"[green]✓ Snippet saved with ID {snippet_id}![/green]")
            
            # Show summary
            summary_parts = [f"Summary: Added '{description}' ({len(content)} characters)"]
            if language:
                summary_parts.append(f"Language: {language}")
            if tag_list:
                summary_parts.append(f"Tags: {', '.join(tag_list)}")
            console.print(f"\n[dim]{chr(10).join(summary_parts)}[/dim]")
            
        except Exception as e:
            console.print(f"[red]Error saving snippet: {e}[/red]")
            raise typer.Exit(1)
        finally:
            db.close()
            
    except typer.Exit:
        raise  # Re-raise typer.Exit without modification
    except Exception as e:
        console.print(f"[red]Error adding snippet: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def find(
    query: Optional[str] = typer.Argument(None, help="Search query"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Use interactive TUI mode"),
    language: Optional[str] = typer.Option(None, "--language", "-l", help="Filter by language"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag")
):
    """Find code snippets."""
    ensure_database_exists()
    
    db = Database(get_db_path())
    try:
        # For interactive mode without query, get all snippets
        if interactive and not query:
            snippets = db.get_all_snippets()
            
            if not snippets:
                console.print("[yellow]No snippets found. Add some with 'codx add'.[/yellow]")
                raise typer.Exit(0)
            
            # Apply filters for interactive mode
            if language:
                snippets = [s for s in snippets if s.get('language', '').lower() == language.lower()]
            
            if tag:
                snippets = [s for s in snippets if tag.lower() in [t.lower() for t in s.get('tags', [])]]
            
            if not snippets:
                console.print("[yellow]No snippets match the specified filters.[/yellow]")
                raise typer.Exit(0)
        
        # Interactive TUI mode
        if interactive:
            try:
                app = SnippetFinderApp(snippets)
                result = app.run()
                
                if result:
                    if isinstance(result, dict) and 'action' in result:
                        # New format with action
                        action = result['action']
                        snippet = result['snippet']
                        
                        if action == 'copy':
                            pyperclip.copy(snippet['content'])
                            console.print(f"[green]✓ Snippet {snippet['id']} copied to clipboard![/green]")
                            _display_snippet_details(snippet)
                        elif action == 'run':
                            _display_snippet_details(snippet)
                            if Confirm.ask("\nExecute this snippet?"):
                                execute_snippet(snippet['content'], snippet.get('language'))
                            else:
                                console.print("[yellow]Execution cancelled.[/yellow]")
                        elif action == 'edit':
                            console.print(f"[yellow]Use 'codx edit {snippet['id']}' to edit this snippet.[/yellow]")
                        elif action == 'view':
                            # Display detailed view
                            _display_snippet_details(snippet)
                        elif action == 'delete':
                            # Confirm and delete
                            if Confirm.ask(f"Are you sure you want to delete snippet '{snippet['description']}'?"):
                                db.delete_snippet(snippet['id'])
                                console.print(f"[green]✓ Snippet {snippet['id']} deleted successfully![/green]")
                            else:
                                console.print("[yellow]Deletion cancelled.[/yellow]")
                    else:
                        # Legacy format - treat as copied snippet
                        console.print(f"[green]✓ Snippet {result['id']} copied to clipboard![/green]")
                        _display_snippet_details(result)
                else:
                    console.print("[yellow]No action performed.[/yellow]")
                    
            except Exception as e:
                console.print(f"[red]Error running interactive mode: {e}[/red]")
                console.print("[yellow]Falling back to standard search mode...[/yellow]")
                # Fall back to standard mode
                interactive = False
        
        # Standard search mode
        if not interactive:
            # Perform search if query provided
            if query:
                results = search_snippets(db, query, language_filter=language, tag_filter=tag)
                if not results:
                    console.print(f"[yellow]No snippets found matching '{query}'.[/yellow]")
                    raise typer.Exit(0)
                snippets = results
            else:
                # No query provided - get all snippets and apply filters
                snippets = db.get_all_snippets()
                
                if not snippets:
                    console.print("[yellow]No snippets found. Add some with 'codx add'.[/yellow]")
                    raise typer.Exit(0)
                
                # Apply filters when no query is provided
                if language:
                    snippets = [s for s in snippets if s.get('language', '').lower() == language.lower()]
                
                if tag:
                    snippets = [s for s in snippets if tag.lower() in [t.lower() for t in s.get('tags', [])]]
                
                if not snippets:
                    console.print("[yellow]No snippets match the specified filters.[/yellow]")
                    raise typer.Exit(0)
            
            # Display results in table format
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="dim", width=6)
            table.add_column("Description", min_width=20)
            table.add_column("Language", width=12)
            table.add_column("Tags", width=20)
            
            for snippet in snippets[:20]:  # Limit to 20 results
                tags_str = ", ".join(snippet.get('tags', [])[:3])  # Show max 3 tags
                if len(snippet.get('tags', [])) > 3:
                    tags_str += "..."
                
                table.add_row(
                    str(snippet['id']),
                    snippet['description'][:50] + ("..." if len(snippet['description']) > 50 else ""),
                    snippet.get('language', 'None'),
                    tags_str or "None"
                )
            
            console.print(table)
            
            if len(snippets) > 20:
                console.print(f"\n[dim]Showing first 20 of {len(snippets)} results. Use --interactive for better navigation.[/dim]")
            
            console.print("\n[dim]Use 'codx get <id>' to copy a snippet or 'codx find --interactive' for TUI mode.[/dim]")
            
    except typer.Exit:
        raise  # Re-raise typer.Exit without modification
    except Exception as e:
        console.print(f"[red]Error searching snippets: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()

@app.command()
def get(
    snippet_id: int = typer.Argument(..., help="ID of the snippet to get")
):
    """Get a code snippet and copy it to clipboard."""
    ensure_database_exists()
    
    db = Database(get_db_path())
    try:
        snippet = db.get_snippet_by_id(snippet_id)
        
        if not snippet:
            console.print(f"[red]Snippet with ID {snippet_id} not found.[/red]")
            raise typer.Exit(1)
        
        # Try to copy to clipboard
        try:
            pyperclip.copy(snippet['content'])
            console.print(f"[green]✓ Snippet {snippet_id} copied to clipboard![/green]")
        except Exception as e:
            console.print(f"[yellow]⚠ Could not copy to clipboard: {e}[/yellow]")
        
        # Display snippet details
        _display_snippet_details(snippet)
        
    except typer.Exit:
        raise  # Re-raise typer.Exit without modification
    except Exception as e:
        console.print(f"[red]Error retrieving snippet: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()

@app.command()
def run(
    snippet_id: int = typer.Argument(..., help="ID of the snippet to run")
):
    """Execute a code snippet."""
    ensure_database_exists()
    
    db = Database(get_db_path())
    try:
        snippet = db.get_snippet_by_id(snippet_id)
        
        if not snippet:
            console.print(f"[red]Snippet with ID {snippet_id} not found.[/red]")
            raise typer.Exit(1)
        
        # Display snippet details
        _display_snippet_details(snippet)
        
        # Confirm execution
        if not Confirm.ask("\nExecute this snippet?"):
            console.print("[yellow]Execution cancelled.[/yellow]")
            raise typer.Exit(0)
        
        # Execute the snippet
        execute_snippet(snippet['content'], snippet.get('language'))
        
    except typer.Exit:
        raise  # Re-raise typer.Exit without modification
    except Exception as e:
        console.print(f"[red]Error running snippet: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()

@app.command()
def edit(
    snippet_id: int = typer.Argument(..., help="ID of the snippet to edit")
):
    """Edit an existing code snippet."""
    ensure_database_exists()
    
    db = Database(get_db_path())
    try:
        snippet = db.get_snippet_by_id(snippet_id)
        
        if not snippet:
            console.print(f"[red]Snippet with ID {snippet_id} not found.[/red]")
            raise typer.Exit(1)
        
        # Display current snippet
        console.print(f"\n[bold]Editing Snippet {snippet_id}:[/bold]")
        
        details = f"Description: {snippet['description'] or 'None'}\n"
        details += f"Language: {snippet['language'] or 'None'}\n"
        details += f"Tags: {', '.join(snippet['tags']) if snippet['tags'] else 'None'}"
        
        console.print(Panel(details, title="Current Details", border_style="blue"))
        
        # Show current code
        if snippet['language']:
            syntax = Syntax(snippet['content'], snippet['language'], theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title="Current Content", border_style="green"))
        else:
            console.print(Panel(snippet['content'], title="Current Content", border_style="green"))
        
        console.print("\n[yellow]What would you like to edit?[/yellow]")
        console.print("1. Description")
        console.print("2. Content")
        console.print("3. Language")
        console.print("4. Tags")
        console.print("5. All fields")
        
        choice = Prompt.ask("Enter your choice", choices=["1", "2", "3", "4", "5"], default="5")
        
        new_description = snippet['description']
        new_content = snippet['content']
        new_language = snippet['language']
        new_tags = snippet['tags']
        
        if choice in ["1", "5"]:
            new_description = Prompt.ask("Enter new description", default=snippet['description'] or "")
        
        if choice in ["2", "5"]:
            console.print("\n[yellow]Enter new content (press Ctrl+D when finished):[/yellow]")
            console.print("[dim]Current content will be replaced entirely[/dim]")
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                new_content = "\n".join(lines)
            except KeyboardInterrupt:
                console.print("\n[yellow]Edit cancelled by user.[/yellow]")
                raise typer.Exit(0)
        
        if choice in ["3", "5"]:
            new_language = Prompt.ask("Enter programming language", default=snippet['language'] or "")
        
        if choice in ["4", "5"]:
            current_tags = ', '.join(snippet['tags']) if snippet['tags'] else ""
            tags_input = Prompt.ask("Enter tags (comma-separated)", default=current_tags)
            if tags_input.strip():
                new_tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
            else:
                new_tags = []
        
        # Validate new content
        if not new_content or not new_content.strip():
            console.print("[red]Error: Snippet content cannot be empty.[/red]")
            raise typer.Exit(1)
        
        if not new_description or not new_description.strip():
            console.print("[red]Error: Description cannot be empty.[/red]")
            raise typer.Exit(1)
        
        # Show preview of changes
        console.print("\n[bold]Preview of changes:[/bold]")
        
        preview_content = f"Description: {new_description}\n"
        preview_content += f"Language: {new_language or 'None'}\n"
        preview_content += f"Tags: {', '.join(new_tags) if new_tags else 'None'}"
        
        console.print(Panel(preview_content, title="New Details", border_style="blue"))
        
        # Show new code
        if new_language:
            syntax = Syntax(new_content, new_language, theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title="New Content", border_style="green"))
        else:
            console.print(Panel(new_content, title="New Content", border_style="green"))
        
        # Check for variables
        variables = extract_variables(new_content)
        if variables:
            console.print(f"\n[cyan]Variables detected: {', '.join(variables)}[/cyan]")
        
        if not Confirm.ask("\nSave these changes?"):
            console.print("[yellow]Changes not saved.[/yellow]")
            raise typer.Exit(0)
        
        # Update in database
        db.update_snippet(
            snippet_id=snippet_id,
            description=new_description,
            content=new_content,
            language=new_language,
            tags=new_tags
        )
        
        console.print(f"[green]✓ Snippet {snippet_id} updated successfully![/green]")
        
    except typer.Exit:
        raise  # Re-raise typer.Exit without modification
    except Exception as e:
        console.print(f"[red]Error editing snippet: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()