"""Tests for the utils module."""

import pytest
import tempfile
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call

from codx.utils import (
    extract_variables,
    substitute_variables,
    prompt_for_variables,
    execute_snippet,
    get_file_extension,
    open_editor_for_content,
    fuzzy_search_snippets,
    display_snippet_table
)


class TestExtractVariables:
    """Test cases for extract_variables function."""
    
    def test_extract_variables_basic(self):
        """Test extracting basic variables from content."""
        content = "Hello {{name}}, welcome to {{place}}!"
        variables = extract_variables(content)
        assert set(variables) == {"name", "place"}
    
    def test_extract_variables_no_variables(self):
        """Test content with no variables."""
        content = "Hello world, no variables here!"
        variables = extract_variables(content)
        assert variables == []
    
    def test_extract_variables_duplicate(self):
        """Test content with duplicate variables."""
        content = "{{name}} says hello to {{name}} again!"
        variables = extract_variables(content)
        assert variables == ["name"]  # Should be unique
    
    def test_extract_variables_nested_braces(self):
        """Test content with nested or malformed braces."""
        content = "{{name}} and {{{invalid}}} and {{valid}}"
        variables = extract_variables(content)
        assert "name" in variables
        assert "valid" in variables
        assert "invalid" not in variables
    
    def test_extract_variables_empty_content(self):
        """Test empty content."""
        variables = extract_variables("")
        assert variables == []
    
    def test_extract_variables_special_characters(self):
        """Test variables with special characters."""
        content = "{{user_name}} and {{file-path}} and {{var123}}"
        variables = extract_variables(content)
        assert set(variables) == {"user_name", "file-path", "var123"}
    
    def test_extract_variables_multiline(self):
        """Test variables in multiline content."""
        content = """Line 1: {{var1}}
Line 2: {{var2}}
Line 3: {{var1}} again"""
        variables = extract_variables(content)
        assert set(variables) == {"var1", "var2"}


class TestSubstituteVariables:
    """Test cases for substitute_variables function."""
    
    def test_substitute_variables_basic(self):
        """Test basic variable substitution."""
        content = "Hello {{name}}, welcome to {{place}}!"
        variables = {"name": "Alice", "place": "Python"}
        result = substitute_variables(content, variables)
        assert result == "Hello Alice, welcome to Python!"
    
    def test_substitute_variables_missing_variable(self):
        """Test substitution with missing variable."""
        content = "Hello {{name}}, welcome to {{place}}!"
        variables = {"name": "Alice"}
        result = substitute_variables(content, variables)
        assert result == "Hello Alice, welcome to {{place}}!"
    
    def test_substitute_variables_extra_variables(self):
        """Test substitution with extra variables."""
        content = "Hello {{name}}!"
        variables = {"name": "Alice", "extra": "unused"}
        result = substitute_variables(content, variables)
        assert result == "Hello Alice!"
    
    def test_substitute_variables_empty_content(self):
        """Test substitution with empty content."""
        result = substitute_variables("", {"name": "Alice"})
        assert result == ""
    
    def test_substitute_variables_no_variables(self):
        """Test substitution with no variables in content."""
        content = "Hello world!"
        result = substitute_variables(content, {"name": "Alice"})
        assert result == "Hello world!"
    
    def test_substitute_variables_duplicate_variables(self):
        """Test substitution with duplicate variables."""
        content = "{{name}} says hello to {{name}}!"
        variables = {"name": "Alice"}
        result = substitute_variables(content, variables)
        assert result == "Alice says hello to Alice!"
    
    def test_substitute_variables_multiline(self):
        """Test substitution in multiline content."""
        content = """Name: {{name}}
Age: {{age}}
City: {{city}}"""
        variables = {"name": "Alice", "age": "30", "city": "New York"}
        result = substitute_variables(content, variables)
        expected = """Name: Alice
Age: 30
City: New York"""
        assert result == expected


class TestPromptForVariables:
    """Test cases for prompt_for_variables function."""
    
    @patch('builtins.input')
    def test_prompt_for_variables_basic(self, mock_input):
        """Test prompting for variables."""
        mock_input.side_effect = ["Alice", "Python"]
        variables = ["name", "language"]
        result = prompt_for_variables(variables)
        assert result == {"name": "Alice", "language": "Python"}
    
    @patch('builtins.input')
    def test_prompt_for_variables_empty_list(self, mock_input):
        """Test prompting with empty variable list."""
        result = prompt_for_variables([])
        assert result == {}
        mock_input.assert_not_called()
    
    @patch('builtins.input')
    def test_prompt_for_variables_empty_input(self, mock_input):
        """Test prompting with empty user input."""
        mock_input.side_effect = ["", "Python"]
        variables = ["name", "language"]
        result = prompt_for_variables(variables)
        assert result == {"name": "", "language": "Python"}
    
    @patch('builtins.input')
    def test_prompt_for_variables_keyboard_interrupt(self, mock_input):
        """Test handling keyboard interrupt during prompting."""
        mock_input.side_effect = KeyboardInterrupt()
        variables = ["name"]
        result = prompt_for_variables(variables)
        assert result == {}


class TestExecuteSnippet:
    """Test cases for execute_snippet function."""
    
    @patch('subprocess.run')
    def test_execute_snippet_python(self, mock_run):
        """Test executing a Python snippet."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Hello, World!\n"
        mock_run.return_value.stderr = ""
        
        content = "print('Hello, World!')"
        language = "python"
        
        result = execute_snippet(content, language)
        assert result['success'] is True
        assert result['output'] == "Hello, World!\n"
        assert result['error'] == ""
        
        # Verify subprocess was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "python" in call_args[0][0]
    
    @patch('subprocess.run')
    def test_execute_snippet_javascript(self, mock_run):
        """Test executing a JavaScript snippet."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Hello from JS\n"
        mock_run.return_value.stderr = ""
        
        content = "console.log('Hello from JS')"
        language = "javascript"
        
        result = execute_snippet(content, language)
        assert result['success'] is True
        assert result['output'] == "Hello from JS\n"
        
        # Verify node was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "node" in call_args[0][0]
    
    @patch('subprocess.run')
    def test_execute_snippet_bash(self, mock_run):
        """Test executing a Bash snippet."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Hello from bash\n"
        mock_run.return_value.stderr = ""
        
        content = "echo 'Hello from bash'"
        language = "bash"
        
        result = execute_snippet(content, language)
        assert result['success'] is True
        assert result['output'] == "Hello from bash\n"
        
        # Verify bash was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "bash" in call_args[0][0]
    
    @patch('subprocess.run')
    def test_execute_snippet_error(self, mock_run):
        """Test executing a snippet that produces an error."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "SyntaxError: invalid syntax\n"
        
        content = "print('unclosed string"
        language = "python"
        
        result = execute_snippet(content, language)
        assert result['success'] is False
        assert result['error'] == "SyntaxError: invalid syntax\n"
    
    @patch('subprocess.run')
    def test_execute_snippet_timeout(self, mock_run):
        """Test executing a snippet that times out."""
        mock_run.side_effect = subprocess.TimeoutExpired("python", 30)
        
        content = "import time; time.sleep(100)"
        language = "python"
        
        result = execute_snippet(content, language)
        assert result['success'] is False
        assert "timeout" in result['error'].lower()
    
    def test_execute_snippet_unsupported_language(self):
        """Test executing a snippet with unsupported language."""
        content = "some code"
        language = "unsupported"
        
        result = execute_snippet(content, language)
        assert result['success'] is False
        assert "not supported" in result['error'].lower()
    
    @patch('subprocess.run')
    def test_execute_snippet_with_variables(self, mock_run):
        """Test executing a snippet with variable substitution."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Hello, Alice!\n"
        mock_run.return_value.stderr = ""
        
        content = "print('Hello, {{name}}!')"
        language = "python"
        variables = {"name": "Alice"}
        
        result = execute_snippet(content, language, variables)
        assert result['success'] is True
        assert result['output'] == "Hello, Alice!\n"


class TestGetFileExtension:
    """Test cases for get_file_extension function."""
    
    def test_get_file_extension_python(self):
        """Test getting extension for Python language."""
        assert get_file_extension("python") == ".py"
    
    def test_get_file_extension_javascript(self):
        """Test getting extension for JavaScript language."""
        assert get_file_extension("javascript") == ".js"
    
    def test_get_file_extension_bash(self):
        """Test getting extension for Bash language."""
        assert get_file_extension("bash") == ".sh"
    
    def test_get_file_extension_unknown(self):
        """Test getting extension for unknown language."""
        assert get_file_extension("unknown") == ".txt"
    
    def test_get_file_extension_case_insensitive(self):
        """Test case insensitive language matching."""
        assert get_file_extension("Python") == ".py"
        assert get_file_extension("JAVASCRIPT") == ".js"
    
    def test_get_file_extension_aliases(self):
        """Test language aliases."""
        assert get_file_extension("js") == ".js"
        assert get_file_extension("py") == ".py"
        assert get_file_extension("sh") == ".sh"


class TestOpenEditorForContent:
    """Test cases for open_editor_for_content function."""
    
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_open_editor_basic(self, mock_tempfile, mock_run):
        """Test opening editor with basic content."""
        # Mock temporary file
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.py"
        mock_tempfile.return_value.__enter__.return_value = mock_file
        
        # Mock subprocess (editor)
        mock_run.return_value.returncode = 0
        
        # Mock reading the modified file
        modified_content = "print('modified')"
        with patch('builtins.open', mock_open(read_data=modified_content)):
            result = open_editor_for_content("print('original')", "python")
        
        assert result == modified_content
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_open_editor_with_custom_editor(self, mock_tempfile, mock_run):
        """Test opening editor with custom EDITOR environment variable."""
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.py"
        mock_tempfile.return_value.__enter__.return_value = mock_file
        
        mock_run.return_value.returncode = 0
        
        with patch.dict(os.environ, {'EDITOR': 'vim'}):
            with patch('builtins.open', mock_open(read_data="modified")):
                result = open_editor_for_content("original", "python")
        
        # Verify vim was called
        call_args = mock_run.call_args[0][0]
        assert "vim" in call_args
    
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_open_editor_error(self, mock_tempfile, mock_run):
        """Test handling editor errors."""
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.py"
        mock_tempfile.return_value.__enter__.return_value = mock_file
        
        # Mock editor failure
        mock_run.side_effect = subprocess.CalledProcessError(1, "editor")
        
        result = open_editor_for_content("original", "python")
        assert result == "original"  # Should return original content on error


class TestFuzzySearchSnippets:
    """Test cases for fuzzy_search_snippets function."""
    
    def test_fuzzy_search_basic(self):
        """Test basic fuzzy search functionality."""
        snippets = [
            {'id': 1, 'description': 'Python Hello World', 'content': 'print("hello")', 'language': 'python', 'tags': ['python']},
            {'id': 2, 'description': 'JavaScript Function', 'content': 'function hello()', 'language': 'javascript', 'tags': ['js']},
            {'id': 3, 'description': 'Bash Script', 'content': 'echo hello', 'language': 'bash', 'tags': ['bash']}
        ]
        
        results = fuzzy_search_snippets(snippets, "hello")
        assert len(results) == 3  # All contain "hello"
        
        # Results should be sorted by relevance
        descriptions = [r['description'] for r in results]
        assert "Python Hello World" in descriptions
    
    def test_fuzzy_search_no_query(self):
        """Test fuzzy search with empty query."""
        snippets = [
            {'id': 1, 'description': 'Test', 'content': 'test', 'language': 'python', 'tags': []}
        ]
        
        results = fuzzy_search_snippets(snippets, "")
        assert results == snippets  # Should return all snippets
    
    def test_fuzzy_search_no_matches(self):
        """Test fuzzy search with no matches."""
        snippets = [
            {'id': 1, 'description': 'Python script', 'content': 'print("test")', 'language': 'python', 'tags': ['python']}
        ]
        
        results = fuzzy_search_snippets(snippets, "javascript")
        assert results == []  # No matches
    
    def test_fuzzy_search_language_filter(self):
        """Test fuzzy search with language filter."""
        snippets = [
            {'id': 1, 'description': 'Python Hello', 'content': 'print("hello")', 'language': 'python', 'tags': []},
            {'id': 2, 'description': 'JS Hello', 'content': 'console.log("hello")', 'language': 'javascript', 'tags': []}
        ]
        
        results = fuzzy_search_snippets(snippets, "hello", language="python")
        assert len(results) == 1
        assert results[0]['language'] == 'python'
    
    def test_fuzzy_search_tags_filter(self):
        """Test fuzzy search with tags filter."""
        snippets = [
            {'id': 1, 'description': 'Test 1', 'content': 'test', 'language': 'python', 'tags': ['basic', 'tutorial']},
            {'id': 2, 'description': 'Test 2', 'content': 'test', 'language': 'python', 'tags': ['advanced']}
        ]
        
        results = fuzzy_search_snippets(snippets, "", tags=["basic"])
        assert len(results) == 1
        assert 'basic' in results[0]['tags']
    
    def test_fuzzy_search_combined_filters(self):
        """Test fuzzy search with multiple filters."""
        snippets = [
            {'id': 1, 'description': 'Python Hello', 'content': 'print("hello")', 'language': 'python', 'tags': ['basic']},
            {'id': 2, 'description': 'Python Goodbye', 'content': 'print("bye")', 'language': 'python', 'tags': ['advanced']},
            {'id': 3, 'description': 'JS Hello', 'content': 'console.log("hello")', 'language': 'javascript', 'tags': ['basic']}
        ]
        
        results = fuzzy_search_snippets(snippets, "hello", language="python", tags=["basic"])
        assert len(results) == 1
        assert results[0]['id'] == 1


class TestDisplaySnippetTable:
    """Test cases for display_snippet_table function."""
    
    @patch('rich.console.Console.print')
    def test_display_snippet_table_basic(self, mock_print):
        """Test displaying basic snippet table."""
        snippets = [
            {
                'id': 1,
                'description': 'Test snippet',
                'language': 'python',
                'tags': ['test'],
                'created_at': '2023-01-01 12:00:00'
            }
        ]
        
        display_snippet_table(snippets)
        
        # Verify console.print was called
        mock_print.assert_called()
        
        # Check that table was created with snippet data
        call_args = mock_print.call_args_list
        table_call = None
        for call in call_args:
            if hasattr(call[0][0], 'add_row'):  # Rich Table object
                table_call = call
                break
        
        assert table_call is not None
    
    @patch('rich.console.Console.print')
    def test_display_snippet_table_empty(self, mock_print):
        """Test displaying empty snippet table."""
        display_snippet_table([])
        
        # Should still print something (empty table or message)
        mock_print.assert_called()
    
    @patch('rich.console.Console.print')
    def test_display_snippet_table_multiple(self, mock_print):
        """Test displaying table with multiple snippets."""
        snippets = [
            {
                'id': 1,
                'description': 'Python snippet',
                'language': 'python',
                'tags': ['python', 'basic'],
                'created_at': '2023-01-01 12:00:00'
            },
            {
                'id': 2,
                'description': 'JS snippet',
                'language': 'javascript',
                'tags': ['js'],
                'created_at': '2023-01-02 12:00:00'
            }
        ]
        
        display_snippet_table(snippets)
        
        # Verify console.print was called
        mock_print.assert_called()
    
    @patch('rich.console.Console.print')
    def test_display_snippet_table_long_description(self, mock_print):
        """Test displaying table with long description."""
        snippets = [
            {
                'id': 1,
                'description': 'A very long description that should be truncated or handled properly by the table display function',
                'language': 'python',
                'tags': ['test'],
                'created_at': '2023-01-01 12:00:00'
            }
        ]
        
        display_snippet_table(snippets)
        
        # Should handle long descriptions gracefully
        mock_print.assert_called()
    
    @patch('rich.console.Console.print')
    def test_display_snippet_table_no_tags(self, mock_print):
        """Test displaying table with snippets that have no tags."""
        snippets = [
            {
                'id': 1,
                'description': 'No tags snippet',
                'language': 'python',
                'tags': [],
                'created_at': '2023-01-01 12:00:00'
            }
        ]
        
        display_snippet_table(snippets)
        
        # Should handle empty tags gracefully
        mock_print.assert_called()