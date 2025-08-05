"""Main TUI application for codx."""

from typing import List
from textual.app import App
from .screens import SnippetListScreen


class SnippetFinderApp(App):
    """A Textual app for interactive snippet searching."""
    
    CSS = """
    Screen {
        background: $background;
    }
    
    #search-input {
        dock: top;
        height: 3;
        margin: 1;
    }
    
    #results-table {
        height: 1fr;
        margin: 0 1;
    }
    
    #view-container, #edit-container, #run-container {
        padding: 1;
        height: 1fr;
    }
    
    #description {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    #language, #tags {
        margin-bottom: 1;
    }
    
    #content-label, #edit-label, #code-label, #output-label {
        text-style: bold;
        margin-top: 1;
        margin-bottom: 1;
    }
    
    #content, #edit-content, #run-code {
        background: $surface;
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
    }
    
    #run-output {
        background: $surface;
        border: solid $secondary;
        padding: 1;
        margin-bottom: 1;
        height: 1fr;
    }
    
    #help-text, #edit-help, #run-help {
        color: $text-muted;
        text-style: italic;
    }
    
    #edit-title, #run-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    """
    
    def __init__(self, snippets: List[dict]):
        super().__init__()
        self.snippets = snippets
    
    def on_mount(self) -> None:
        """Push the snippet list screen when the app starts."""
        self.push_screen(SnippetListScreen(self.snippets))