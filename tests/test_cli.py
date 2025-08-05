"""Tests for the CLI commands module."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from typer.testing import CliRunner
from click.testing import Result

from codx.cli.commands import app
from codx.core.database import Database


class TestCLICommands:
    """Test cases for CLI commands."""
    
    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        yield db_path
        
        try:
            os.unlink(db_path)
        except OSError:
            pass
    
    @pytest.fixture
    def setup_test_db(self, temp_db_path):
        """Set up a test database with sample data."""
        db = Database(temp_db_path)
        db.initialize_database()
        
        # Add sample snippets
        python_id = db.add_snippet(
            description="Python Hello World",
            content="print('Hello, World!')",
            language="python",
            tags=["python", "basic"]
        )
        
        js_id = db.add_snippet(
            description="JavaScript Function",
            content="function greet(name) { return `Hello, ${name}!`; }",
            language="javascript",
            tags=["javascript", "function"]
        )
        
        db.close()
        
        return {
            'db_path': temp_db_path,
            'python_id': python_id,
            'js_id': js_id
        }
    
    def test_cli_help(self, runner):
        """Test the main help command."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "CODX" in result.stdout
        assert "Commands" in result.stdout
        assert "add" in result.stdout
        assert "find" in result.stdout
        assert "get" in result.stdout
        assert "run" in result.stdout
    
    def test_init_command(self, runner, temp_db_path):
        """Test the init command."""
        with patch('codx.cli.commands.get_db_path', return_value=temp_db_path):
            result = runner.invoke(app, ["init", "--force"])
            assert result.exit_code == 0
            assert "Database initialized" in result.stdout
            
            # Verify database file was created
            assert os.path.exists(temp_db_path)
    
    def test_init_command_existing_db(self, runner, setup_test_db):
        """Test init command when database already exists."""
        db_path = setup_test_db['db_path']
        
        with patch('codx.cli.commands.get_db_path', return_value=db_path):
            result = runner.invoke(app, ["init", "--force"])
            assert result.exit_code == 0
            assert "Database initialized" in result.stdout
    
    @patch('codx.cli.commands.get_db_path')
    @patch('codx.cli.commands.ensure_database_exists')
    @patch('rich.prompt.Confirm.ask', return_value=True)  # Confirm save
    @patch('rich.prompt.Prompt.ask', return_value="")  # Mock prompts
    def test_add_command_basic(self, mock_prompt, mock_confirm, mock_ensure_db, mock_get_db_path, runner, temp_db_path):
        """Test adding a snippet via CLI."""
        mock_get_db_path.return_value = temp_db_path
        
        # Initialize database first
        db = Database(temp_db_path)
        db.initialize_database()
        db.close()
        
        result = runner.invoke(app, [
            "add",
            "--description", "Test snippet",
            "--content", "print('test')",
            "--language", "python",
            "--tags", "test,python"
        ])
        
        assert result.exit_code == 0
        assert "Snippet saved" in result.stdout
    
    @patch('codx.cli.commands.get_db_path')
    @patch('codx.cli.commands.ensure_database_exists')
    @patch('rich.prompt.Confirm.ask', return_value=False)  # Don't save
    @patch('rich.prompt.Prompt.ask', return_value="")  # Mock prompts
    def test_add_command_cancel(self, mock_prompt, mock_confirm, mock_ensure_db, mock_get_db_path, runner, temp_db_path):
        """Test canceling snippet addition."""
        mock_get_db_path.return_value = temp_db_path
        
        # Initialize database first
        db = Database(temp_db_path)
        db.initialize_database()
        db.close()
        
        result = runner.invoke(app, [
            "add",
            "--description", "Test snippet",
            "--content", "print('test')",
            "--language", "python"
        ])
        
        assert result.exit_code == 0
        assert "Snippet not saved" in result.stdout
    
    @patch('codx.cli.commands.get_db_path')
    @patch('codx.cli.commands.ensure_database_exists')
    def test_add_command_from_file(self, mock_ensure_db, mock_get_db_path, runner, temp_db_path):
        """Test adding a snippet from a file."""
        mock_get_db_path.return_value = temp_db_path
        
        # Initialize database
        db = Database(temp_db_path)
        db.initialize_database()
        db.close()
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write("print('Hello from file')")
            file_path = tmp.name
        
        try:
            with patch('rich.prompt.Confirm.ask', return_value=True):
                with patch('rich.prompt.Prompt.ask', return_value=""):
                    result = runner.invoke(app, [
                        "add",
                        "--file", file_path,
                        "--description", "From file",
                        "--language", "python"
                    ])
                
                assert result.exit_code == 0
                assert "Snippet saved" in result.stdout
        finally:
            os.unlink(file_path)
    
    @patch('codx.cli.commands.get_db_path')
    def test_find_command_basic(self, mock_get_db_path, runner, setup_test_db):
        """Test basic find command."""
        mock_get_db_path.return_value = setup_test_db['db_path']
        
        result = runner.invoke(app, ["find"])
        assert result.exit_code == 0
        assert "Python Hello World" in result.stdout
        assert "JavaScript Function" in result.stdout
    
    @patch('codx.cli.commands.get_db_path')
    def test_find_command_with_query(self, mock_get_db_path, runner, setup_test_db):
        """Test find command with search query."""
        mock_get_db_path.return_value = setup_test_db['db_path']
        
        result = runner.invoke(app, ["find", "python"])
        assert result.exit_code == 0
        assert "Python Hello World" in result.stdout
        assert "JavaScript Function" not in result.stdout
    
    @patch('codx.cli.commands.get_db_path')
    def test_find_command_with_language_filter(self, mock_get_db_path, runner, setup_test_db):
        """Test find command with language filter."""
        mock_get_db_path.return_value = setup_test_db['db_path']
        
        result = runner.invoke(app, ["find", "--language", "javascript"])
        assert result.exit_code == 0
        assert "JavaScript Function" in result.stdout
        assert "Python Hello World" not in result.stdout
    
    @patch('codx.cli.commands.get_db_path')
    def test_find_command_with_tags_filter(self, mock_get_db_path, runner, setup_test_db):
        """Test find command with tags filter."""
        mock_get_db_path.return_value = setup_test_db['db_path']
        
        result = runner.invoke(app, ["find", "--tag", "basic"])
        assert result.exit_code == 0
        assert "Python Hello World" in result.stdout
    
    @patch('codx.cli.commands.get_db_path')
    def test_find_command_no_results(self, mock_get_db_path, runner, setup_test_db):
        """Test find command with no matching results."""
        mock_get_db_path.return_value = setup_test_db['db_path']
        
        result = runner.invoke(app, ["find", "nonexistent"])
        assert result.exit_code == 0
        assert "No snippets found" in result.stdout
    
    @patch('codx.cli.commands.get_db_path')
    @patch('pyperclip.copy')
    def test_get_command_basic(self, mock_copy, mock_get_db_path, runner, setup_test_db):
        """Test get command to retrieve a snippet."""
        mock_get_db_path.return_value = setup_test_db['db_path']
        snippet_id = setup_test_db['python_id']
        
        result = runner.invoke(app, ["get", str(snippet_id)])
        assert result.exit_code == 0
        assert "Python Hello World" in result.stdout
        assert "print('Hello, World!')" in result.stdout
        
        # Verify content was copied to clipboard
        mock_copy.assert_called_once_with("print('Hello, World!')")
    
    @patch('codx.cli.commands.get_db_path')
    def test_get_command_nonexistent(self, mock_get_db_path, runner, setup_test_db):
        """Test get command with non-existent snippet ID."""
        mock_get_db_path.return_value = setup_test_db['db_path']
        
        result = runner.invoke(app, ["get", "999"])
        assert result.exit_code == 1
        assert "Snippet with ID 999 not found" in result.stdout
    
    @patch('codx.cli.commands.get_db_path')
    @patch('rich.prompt.Confirm.ask', return_value=True)
    @patch('codx.cli.commands.execute_snippet')
    def test_run_command_basic(self, mock_execute, mock_confirm, mock_get_db_path, runner, setup_test_db):
        """Test run command to execute a snippet."""
        mock_get_db_path.return_value = setup_test_db['db_path']
        snippet_id = setup_test_db['python_id']
        
        result = runner.invoke(app, ["run", str(snippet_id)])
        assert result.exit_code == 0
        
        # Verify confirmation was asked and execution was called
        mock_confirm.assert_called_once()
        mock_execute.assert_called_once()
    
    @patch('codx.cli.commands.get_db_path')
    def test_run_command_nonexistent(self, mock_get_db_path, runner, setup_test_db):
        """Test run command with non-existent snippet ID."""
        mock_get_db_path.return_value = setup_test_db['db_path']
        
        result = runner.invoke(app, ["run", "999"])
        assert result.exit_code == 1
        assert "Snippet with ID 999 not found" in result.stdout
    
    @patch('codx.cli.commands.get_db_path')
    @patch('rich.prompt.Confirm.ask', return_value=True)  # Confirm save
    @patch('rich.prompt.Prompt.ask', side_effect=['2', 'Modified description'])  # Edit content choice, then description
    @patch('builtins.input', side_effect=['print("Modified Hello, World!")', EOFError()])  # Content input
    def test_edit_command_basic(self, mock_input, mock_prompt, mock_confirm, mock_get_db_path, runner, setup_test_db):
        """Test edit command to modify a snippet."""
        mock_get_db_path.return_value = setup_test_db['db_path']
        snippet_id = setup_test_db['python_id']
        
        result = runner.invoke(app, ["edit", str(snippet_id)])
        assert result.exit_code == 0
        assert "updated successfully" in result.stdout
    
    @patch('codx.cli.commands.get_db_path')
    def test_edit_command_nonexistent(self, mock_get_db_path, runner, setup_test_db):
        """Test edit command with non-existent snippet ID."""
        mock_get_db_path.return_value = setup_test_db['db_path']
        
        result = runner.invoke(app, ["edit", "999"])
        assert result.exit_code == 1
        assert "Snippet with ID 999 not found" in result.stdout
    
    @patch('codx.cli.commands.get_db_path')
    @patch('rich.prompt.Confirm.ask', return_value=True)  # Confirm deletion
    def test_delete_command_basic(self, mock_confirm, mock_get_db_path, runner, setup_test_db):
        """Test delete command to remove a snippet."""
        mock_get_db_path.return_value = setup_test_db['db_path']
        snippet_id = setup_test_db['python_id']
        
        result = runner.invoke(app, ["delete", str(snippet_id)])
        assert result.exit_code == 0
        assert "Snippet deleted" in result.stdout
    
    @patch('codx.cli.commands.get_db_path')
    @patch('rich.prompt.Confirm.ask', return_value=False)  # Cancel deletion
    def test_delete_command_cancel(self, mock_confirm, mock_get_db_path, runner, setup_test_db):
        """Test canceling snippet deletion."""
        mock_get_db_path.return_value = setup_test_db['db_path']
        snippet_id = setup_test_db['python_id']
        
        result = runner.invoke(app, ["delete", str(snippet_id)])
        assert result.exit_code == 0
        assert "Deletion cancelled" in result.stdout
    
    @patch('codx.cli.commands.get_db_path')
    def test_delete_command_nonexistent(self, mock_get_db_path, runner, setup_test_db):
        """Test delete command with non-existent snippet ID."""
        mock_get_db_path.return_value = setup_test_db['db_path']
        
        result = runner.invoke(app, ["delete", "999"])
        assert result.exit_code == 1
        assert "Snippet with ID 999 not found" in result.stdout
    
    def test_invalid_command(self, runner):
        """Test invalid command handling."""
        result = runner.invoke(app, ["invalid_command"])
        assert result.exit_code != 0
    
    @patch('codx.cli.commands.get_db_path')
    def test_database_not_initialized(self, mock_get_db_path, runner, temp_db_path):
        """Test commands when database is not initialized."""
        # Point to non-existent database
        mock_get_db_path.return_value = temp_db_path
        
        result = runner.invoke(app, ["find"])
        assert result.exit_code != 0
        assert "not initialized" in result.stdout or "No such file" in result.stdout or "no such table" in result.stdout
    
    @patch('codx.cli.commands.get_db_path')
    def test_add_command_missing_required_args(self, mock_get_db_path, runner, temp_db_path):
        """Test add command with missing required arguments."""
        mock_get_db_path.return_value = temp_db_path
        
        # Missing description
        result = runner.invoke(app, [
            "add",
            "--content", "print('test')",
            "--language", "python"
        ])
        assert result.exit_code != 0
    
    @patch('codx.cli.commands.get_db_path')
    def test_add_command_file_not_found(self, mock_get_db_path, runner, temp_db_path):
        """Test add command with non-existent file."""
        mock_get_db_path.return_value = temp_db_path
        
        result = runner.invoke(app, [
            "add",
            "--file", "/non/existent/file.py",
            "--description", "Test"
        ])
        assert result.exit_code != 0
        assert "not found" in result.stdout or "No such file" in result.stdout
    
    @patch('codx.cli.commands.get_db_path')
    @patch('codx.tui.app.SnippetFinderApp.run')
    def test_find_interactive_mode(self, mock_tui_run, mock_get_db_path, runner, setup_test_db):
        """Test find command in interactive mode."""
        mock_get_db_path.return_value = setup_test_db['db_path']
        
        result = runner.invoke(app, ["find", "--interactive"])
        assert result.exit_code == 0
        
        # Verify TUI was launched
        mock_tui_run.assert_called_once()
    
    @patch('codx.cli.commands.get_db_path')
    def test_get_command_no_clipboard(self, mock_get_db_path, runner, setup_test_db):
        """Test get command when clipboard is not available."""
        mock_get_db_path.return_value = setup_test_db['db_path']
        snippet_id = setup_test_db['python_id']
        
        with patch('pyperclip.copy', side_effect=Exception("No clipboard")):
            result = runner.invoke(app, ["get", str(snippet_id)])
            assert result.exit_code == 0
            assert "Python Hello World" in result.stdout
            # Should still work even if clipboard fails
    
    @patch('codx.cli.commands.get_db_path')
    @patch('rich.prompt.Confirm.ask', return_value=True)
    @patch('codx.cli.commands.execute_snippet')
    @patch('codx.utils.variables.prompt_for_variables', return_value={'name': 'World'})
    def test_run_command_with_variables(self, mock_prompt_vars, mock_execute, mock_confirm, mock_get_db_path, runner, temp_db_path):
        """Test run command with snippet containing variables."""
        mock_get_db_path.return_value = temp_db_path
        
        # Initialize database and add snippet with variables
        db = Database(temp_db_path)
        db.initialize_database()
        
        snippet_id = db.add_snippet(
            description="Snippet with variables",
            content="print('Hello, {{name}}!')",
            language="python",
            tags=["variables"]
        )
        db.close()
        
        result = runner.invoke(app, ["run", str(snippet_id)])
        assert result.exit_code == 0
        mock_execute.assert_called_once()
    
    @patch('codx.cli.commands.get_db_path')
    def test_export_command(self, mock_get_db_path, runner, setup_test_db):
        """Test export command functionality."""
        mock_get_db_path.return_value = setup_test_db['db_path']
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            export_path = tmp.name
        
        try:
            result = runner.invoke(app, ["export", export_path])
            assert result.exit_code == 0
            assert "exported" in result.stdout
            
            # Verify export file was created
            assert os.path.exists(export_path)
        finally:
            try:
                os.unlink(export_path)
            except OSError:
                pass
    
    @patch('codx.cli.commands.get_db_path')
    def test_import_command(self, mock_get_db_path, runner, temp_db_path):
        """Test import command functionality."""
        mock_get_db_path.return_value = temp_db_path
        
        # Initialize database
        db = Database(temp_db_path)
        db.initialize_database()
        db.close()
        
        # Create a sample import file
        import_data = {
            "snippets": [
                {
                    "description": "Imported snippet",
                    "content": "print('imported')",
                    "language": "python",
                    "tags": ["imported"]
                }
            ]
        }
        
        import json
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(import_data, tmp)
            import_path = tmp.name
        
        try:
            result = runner.invoke(app, ["import", import_path])
            assert result.exit_code == 0
            assert "imported" in result.stdout
        finally:
            try:
                os.unlink(import_path)
            except OSError:
                pass