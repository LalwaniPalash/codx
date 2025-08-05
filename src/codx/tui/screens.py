"""TUI screens for codx."""

import os
import tempfile
import subprocess
import asyncio
import re
import concurrent.futures
from typing import List, Dict, Any

import pyperclip
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Input, DataTable, Footer, Header, Static
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen

from ..utils.variables import extract_variables
from ..utils.execution import get_file_extension
from ..utils.search import fuzzy_search_snippets


class SnippetListScreen(Screen):
    """Main screen showing the list of snippets."""
    
    BINDINGS = [
        Binding("escape,q", "quit", "Quit"),
        Binding("enter,c", "copy_snippet", "Copy"),
        Binding("e", "edit_snippet", "Edit"),
        Binding("r", "run_snippet", "Run"),
        Binding("v", "view_snippet", "View"),
        Binding("d", "delete_snippet", "Delete"),
        Binding("ctrl+c", "quit", "Quit"),
    ]
    
    def __init__(self, snippets: List[dict]):
        super().__init__()
        self.snippets = snippets
        self.filtered_snippets = snippets
        self.selected_snippet = None
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the screen."""
        yield Header()
        yield Input(placeholder="Type to search snippets...", id="search-input")
        yield DataTable(id="results-table")
        yield Footer()
    
    def on_mount(self) -> None:
        """Set up the screen when mounted."""
        table = self.query_one("#results-table", DataTable)
        table.add_columns("ID", "Description", "Language", "Tags")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.update_table()
        
        # Focus the search input
        search_input = self.query_one("#search-input", Input)
        search_input.focus()
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            query = event.value.strip()
            if query:
                # Perform fuzzy search
                self.filtered_snippets = fuzzy_search_snippets(self.snippets, query, 50)
            else:
                self.filtered_snippets = self.snippets
            self.update_table()
    
    def update_table(self) -> None:
        """Update the results table with filtered snippets."""
        table = self.query_one("#results-table", DataTable)
        table.clear()
        
        for snippet in self.filtered_snippets:
            tags_str = ", ".join(snippet['tags'][:3])
            if len(snippet['tags']) > 3:
                tags_str += "..."
            
            table.add_row(
                str(snippet['id']),
                snippet['description'][:50] + ("..." if len(snippet['description']) > 50 else ""),
                snippet['language'] or "N/A",
                tags_str or "N/A",
                key=snippet['id']
            )
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the table."""
        snippet_id = event.row_key
        self.selected_snippet = next((s for s in self.filtered_snippets if s['id'] == snippet_id), None)
    
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row highlighting (cursor movement) in the table."""
        snippet_id = event.row_key
        self.selected_snippet = next((s for s in self.filtered_snippets if s['id'] == snippet_id), None)
    
    def get_selected_snippet(self) -> dict:
        """Get the currently selected snippet."""
        if self.selected_snippet:
            return self.selected_snippet
        
        # If no explicit selection, try to get the row at cursor position
        table = self.query_one("#results-table", DataTable)
        if table.row_count > 0:
            # Try to get the row at cursor position
            try:
                cursor_row = table.cursor_row
                if cursor_row >= 0 and cursor_row < len(self.filtered_snippets):
                    return self.filtered_snippets[cursor_row]
            except (AttributeError, IndexError):
                pass
            
            # Fallback to first row
            first_row_key = list(table.rows.keys())[0] if table.rows else None
            if first_row_key:
                snippet = next((s for s in self.filtered_snippets if s['id'] == first_row_key), None)
                if snippet:
                    return snippet
        return None
    
    def action_copy_snippet(self) -> None:
        """Copy selected snippet to clipboard."""
        snippet = self.get_selected_snippet()
        if snippet:
            try:
                pyperclip.copy(snippet['content'])
                self.notify(f"Copied '{snippet['description'][:30]}...' to clipboard", severity="info")
            except Exception as e:
                self.notify(f"Failed to copy to clipboard: {e}", severity="error")
        else:
            self.notify("No snippet selected", severity="warning")
    
    def action_edit_snippet(self) -> None:
        """Edit the selected snippet."""
        snippet = self.get_selected_snippet()
        if snippet:
            self.app.push_screen(SnippetEditScreen(snippet))
        else:
            self.notify("No snippet selected", severity="warning")
    
    def action_run_snippet(self) -> None:
        """Run the selected snippet."""
        snippet = self.get_selected_snippet()
        if snippet:
            self.app.push_screen(SnippetRunScreen(snippet))
        else:
            self.notify("No snippet selected", severity="warning")
    
    def action_view_snippet(self) -> None:
        """View the selected snippet details."""
        snippet = self.get_selected_snippet()
        if snippet:
            self.app.push_screen(SnippetViewScreen(snippet))
        else:
            self.notify("No snippet selected", severity="warning")
    
    def action_delete_snippet(self) -> None:
        """Delete the selected snippet."""
        snippet = self.get_selected_snippet()
        if snippet:
            self.app.exit({"action": "delete", "snippet": snippet})
        else:
            self.notify("No snippet selected", severity="warning")
    
    def action_quit(self) -> None:
        """Quit the app."""
        self.app.exit()


class SnippetViewScreen(Screen):
    """Screen for viewing snippet details."""
    
    BINDINGS = [
        Binding("[", "go_back", "Back"),
        Binding("escape,q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("c", "copy_content", "Copy"),
    ]
    
    def __init__(self, snippet: dict):
        super().__init__()
        self.snippet = snippet
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the screen."""
        # Format tags
        tags_str = ", ".join(self.snippet['tags']) if self.snippet['tags'] else "No tags"
        
        yield Header()
        yield ScrollableContainer(
            Static(f"📄 {self.snippet['description']}", id="description"),
            Static(f"**Language:** {self.snippet['language'] or 'Not specified'}", id="language"),
            Static(f"**Tags:** {tags_str}", id="tags"),
            Static("**Content:**", id="content-label"),
            Static(self.snippet['content'], id="content"),
            Static("\nPress '[' to go back, 'c' to copy content", id="help-text"),
            id="view-container"
        )
        yield Footer()
    
    def action_go_back(self) -> None:
        """Go back to the snippet list."""
        self.app.pop_screen()
    
    def action_copy_content(self) -> None:
        """Copy snippet content to clipboard."""
        try:
            pyperclip.copy(self.snippet['content'])
            self.notify(f"Copied snippet content to clipboard", severity="information")
        except Exception as e:
            self.notify(f"Failed to copy to clipboard: {e}", severity="error")


class SnippetEditScreen(Screen):
    """Screen for editing snippet content."""
    
    BINDINGS = [
        Binding("[", "go_back", "Back"),
        Binding("escape,q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("e", "open_editor", "Edit"),
    ]
    
    def __init__(self, snippet: dict):
        super().__init__()
        self.snippet = snippet
        self.modified_content = snippet['content']
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the screen."""
        yield Header()
        yield ScrollableContainer(
            Static(f"✏️ Editing: {self.snippet['description']}", id="edit-title"),
            Static(f"**Language:** {self.snippet['language'] or 'Not specified'}", id="edit-language"),
            Static("**Current Content:**", id="edit-label"),
            Static(self.snippet['content'], id="edit-content"),
            Static("\nPress 'e' to open external editor, '[' to go back", id="edit-help"),
            id="edit-container"
        )
        yield Footer()
    
    def action_go_back(self) -> None:
        """Go back to the snippet list."""
        self.app.pop_screen()
    
    def action_open_editor(self) -> None:
        """Open external editor for editing snippet content."""
        try:
            # Get the default editor from environment
            editor = os.environ.get('EDITOR', 'nano')
            
            # Create a temporary file with current content
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as temp_file:
                temp_file.write(self.snippet['content'])
                temp_file_path = temp_file.name
            
            # Suspend the app and open editor
            with self.app.suspend():
                result = subprocess.run([editor, temp_file_path])
                
                if result.returncode == 0:
                    # Read the modified content
                    with open(temp_file_path, 'r') as temp_file:
                        self.modified_content = temp_file.read()
                    
                    # Update the display
                    content_widget = self.query_one("#edit-content", Static)
                    content_widget.update(self.modified_content)
                    
                    self.notify("Content updated. Changes are temporary until saved.", severity="information")
                else:
                    self.notify("Editor was cancelled or failed.", severity="warning")
            
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
                
        except FileNotFoundError:
            self.notify(f"Editor '{editor}' not found. Set EDITOR environment variable.", severity="error")
        except Exception as e:
            self.notify(f"Error opening editor: {e}", severity="error")


class SnippetRunScreen(Screen):
    """Screen for running snippet and showing output."""
    
    BINDINGS = [
        Binding("[", "go_back", "Back"),
        Binding("escape,q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("r", "run_again", "Run Again"),
    ]
    
    # Make is_running a reactive property
    is_running = reactive(False)
    
    def __init__(self, snippet: dict):
        super().__init__()
        self.snippet = snippet
        self.output = "Preparing to run snippet..."
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the screen."""
        yield Header()
        yield ScrollableContainer(
            Static(f"🚀 Running: {self.snippet['description']}", id="run-title"),
            Static(f"**Language:** {self.snippet['language'] or 'Shell/Text'}", id="run-language"),
            Static("**Code:**", id="code-label"),
            Static(self.snippet['content'], id="run-code"),
            Static("**Output:**", id="output-label"),
            Static(self.output, id="run-output"),
            Static("\nPress 'r' to run again, '[' to go back", id="run-help"),
            id="run-container"
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """Execute the snippet when the screen is mounted."""
        self.call_after_refresh(self.run_snippet_async)
    
    async def run_snippet_async(self) -> None:
        """Run the snippet asynchronously."""
        if self.is_running:
            return
            
        self.is_running = True
        output_widget = self.query_one("#run-output", Static)
        
        try:
            # Update status
            output_widget.update("Running snippet...")
            await asyncio.sleep(0.1)  # Allow UI to update
            
            # Handle variables if present
            content = self.snippet['content']
            variables = extract_variables(content)
            
            if variables:
                # For TUI mode, we'll use default values or skip variable substitution
                output_widget.update(f"Variables detected: {', '.join(variables)}\nUsing default values or skipping substitution...")
                await asyncio.sleep(1)
                
                # Simple variable substitution with defaults
                def replace_with_default(match):
                    full_match = match.group(1)
                    if ':' in full_match:
                        var_name, default_value = full_match.split(':', 1)
                        return default_value.strip()
                    else:
                        return f"<{full_match}>"
                
                pattern = r'\{\{([^}]+)\}\}'
                content = re.sub(pattern, replace_with_default, content)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix=get_file_extension(self.snippet['language']), delete=False) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Determine execution command
                language = self.snippet['language']
                if language:
                    lang = language.lower()
                    if lang in ['python', 'py']:
                        cmd = ['python', temp_file_path]
                    elif lang in ['javascript', 'js', 'node']:
                        cmd = ['node', temp_file_path]
                    elif lang in ['bash', 'sh', 'shell']:
                        cmd = ['bash', temp_file_path]
                    elif lang in ['ruby', 'rb']:
                        cmd = ['ruby', temp_file_path]
                    elif lang in ['php']:
                        cmd = ['php', temp_file_path]
                    elif lang in ['perl', 'pl']:
                        cmd = ['perl', temp_file_path]
                    else:
                        cmd = ['bash', temp_file_path]
                else:
                    cmd = ['bash', temp_file_path]
                
                # Execute the command
                output_widget.update(f"Executing: {' '.join(cmd)}\n{'='*50}\n")
                await asyncio.sleep(0.1)
                
                # Run in a separate thread to avoid blocking
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(subprocess.run, cmd, capture_output=True, text=True, timeout=30)
                    result = future.result()
                
                # Format output
                output_text = f"Command: {' '.join(cmd)}\n{'='*50}\n"
                
                if result.stdout:
                    output_text += f"STDOUT:\n{result.stdout}\n"
                
                if result.stderr:
                    output_text += f"STDERR:\n{result.stderr}\n"
                
                output_text += f"{'='*50}\n"
                
                if result.returncode == 0:
                    output_text += "✓ Execution completed successfully"
                else:
                    output_text += f"✗ Execution failed with exit code {result.returncode}"
                
                output_widget.update(output_text)
                
            except subprocess.TimeoutExpired:
                output_widget.update("❌ Execution timed out (30 seconds limit)")
            except FileNotFoundError as e:
                output_widget.update(f"❌ Required interpreter not found: {e}\nMake sure the appropriate interpreter is installed.")
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass
                    
        except Exception as e:
            output_widget.update(f"❌ Error running snippet: {e}")
        finally:
            self.is_running = False
    
    def action_go_back(self) -> None:
        """Go back to the snippet list."""
        self.app.pop_screen()
    
    def action_run_again(self) -> None:
        """Run the snippet again."""
        if not self.is_running:
            self.call_after_refresh(self.run_snippet_async)