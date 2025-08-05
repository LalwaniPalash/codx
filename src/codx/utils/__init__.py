"""Utilities package for CODX."""

from .execution import execute_snippet, get_file_extension, open_editor_for_content
from .variables import extract_variables, prompt_for_variables, substitute_variables
from .search import fuzzy_search_snippets
from .display import display_snippet_table

# Create helpers module for backward compatibility
class helpers:
    """Backward compatibility module for helpers."""
    open_editor_for_content = open_editor_for_content

__all__ = [
    'execute_snippet',
    'get_file_extension',
    'open_editor_for_content',
    'extract_variables', 
    'prompt_for_variables',
    'substitute_variables',
    'fuzzy_search_snippets',
    'display_snippet_table',
    'helpers'
]