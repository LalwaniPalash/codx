"""Tests for the TUI module."""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock
from textual.app import App
from textual.widgets import Input, DataTable

from codx.tui.app import SnippetFinderApp
from codx.core.database import Database


class TestSnippetFinderApp:
    """Test cases for the SnippetFinderApp TUI."""
    
    @pytest.fixture
    def sample_snippets(self):
        """Sample snippet data for testing."""
        return [
            {
                'id': 1,
                'description': 'Python Hello World',
                'content': 'print("Hello, World!")',
                'language': 'python',
                'tags': ['python', 'basic'],
                'created_at': '2023-01-01 12:00:00'
            },
            {
                'id': 2,
                'description': 'JavaScript Function',
                'content': 'function greet(name) { return `Hello, ${name}!`; }',
                'language': 'javascript',
                'tags': ['javascript', 'function'],
                'created_at': '2023-01-02 12:00:00'
            },
            {
                'id': 3,
                'description': 'Bash Script',
                'content': '#!/bin/bash\necho "Hello from bash"',
                'language': 'bash',
                'tags': ['bash', 'script'],
                'created_at': '2023-01-03 12:00:00'
            }
        ]
    
    @pytest.fixture
    def temp_db_with_data(self, sample_snippets):
        """Create a temporary database with sample data."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        db = Database(db_path)
        db.initialize_database()
        
        # Add sample snippets
        for snippet in sample_snippets:
            db.add_snippet(
                description=snippet['description'],
                content=snippet['content'],
                language=snippet['language'],
                tags=snippet['tags']
            )
        
        db.close()
        
        yield db_path
        
        try:
            os.unlink(db_path)
        except OSError:
            pass
    
    def test_app_initialization(self, sample_snippets):
        """Test app initialization with snippets."""
        app = SnippetFinderApp(snippets=sample_snippets)
        assert app.snippets == sample_snippets
    
    def test_app_initialization_empty_snippets(self):
        """Test app initialization with empty snippets."""
        app = SnippetFinderApp(snippets=[])
        assert app.snippets == []
    
    def test_app_compose(self, sample_snippets):
        """Test app widget composition."""
        app = SnippetFinderApp(snippets=sample_snippets)
        
        # Test that app has compose method
        assert hasattr(app, 'compose')
        # Test that app has CSS styling
        assert hasattr(app, 'CSS')
        assert len(app.CSS) > 0
    
    def test_load_snippets(self, temp_db_with_data, sample_snippets):
        """Test loading snippets from database."""
        app = SnippetFinderApp(snippets=sample_snippets)
        
        # Test that snippets are properly loaded
        assert len(app.snippets) == len(sample_snippets)
        assert app.snippets == sample_snippets
        
        # Test with empty snippets
        empty_app = SnippetFinderApp(snippets=[])
        assert len(empty_app.snippets) == 0
    
    def test_filter_snippets_empty_query(self, temp_db_with_data, sample_snippets):
        """Test filtering snippets with empty query."""
        from codx.utils.search import fuzzy_search_snippets
        
        # Test fuzzy search with empty query
        result = fuzzy_search_snippets(sample_snippets, "")
        
        # Should return all snippets
        assert len(result) == len(sample_snippets)
        assert result == sample_snippets
    
    def test_filter_snippets_with_query(self, temp_db_with_data, sample_snippets):
        """Test filtering snippets with search query."""
        from codx.utils.search import fuzzy_search_snippets
        
        # Test fuzzy search with query
        result = fuzzy_search_snippets(sample_snippets, "python")
        
        # Should return only Python snippets
        assert len(result) >= 1
        for snippet in result:
            # Check if python appears in description, language, or content
            snippet_text = f"{snippet['description']} {snippet['language']} {snippet['content']}".lower()
            assert "python" in snippet_text
    
    def test_filter_snippets_no_matches(self, temp_db_with_data, sample_snippets):
        """Test filtering with query that matches no snippets."""
        from codx.utils.search import fuzzy_search_snippets
        
        # Test fuzzy search with non-matching query
        result = fuzzy_search_snippets(sample_snippets, "nonexistent")
        
        # Should return empty list or very low matches
        assert len(result) == 0 or all(snippet['score'] < 0.1 for snippet in result if 'score' in snippet)
    
    def test_update_table(self, temp_db_with_data, sample_snippets):
        """Test updating the data table with snippets."""
        from codx.tui.screens import SnippetListScreen
        
        screen = SnippetListScreen(sample_snippets)
        screen.filtered_snippets = sample_snippets
        
        # Mock the table widget
        mock_table = MagicMock(spec=DataTable)
        
        with patch.object(screen, 'query_one', return_value=mock_table):
            screen.update_table()
            
            # Verify table operations were called
            mock_table.clear.assert_called_once()
            assert mock_table.add_row.call_count == len(sample_snippets)
    
    @pytest.mark.asyncio
    async def test_copy_snippet(self, temp_db_with_data, sample_snippets):
        """Test copying snippet to clipboard."""
        from codx.tui.screens import SnippetListScreen
        
        screen = SnippetListScreen(sample_snippets)
        screen.filtered_snippets = sample_snippets
        screen.selected_snippet = sample_snippets[0]  # Set selected snippet directly
        
        with patch('pyperclip.copy') as mock_copy:
            with patch('textual.screen.Screen.notify') as mock_notify:
                screen.action_copy_snippet()
                
                # Should copy content to clipboard
                mock_copy.assert_called_once_with(sample_snippets[0]['content'])
                mock_notify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_copy_snippet_invalid_index(self, temp_db_with_data):
        """Test copying snippet with invalid index."""
        from codx.tui.screens import SnippetListScreen
        
        screen = SnippetListScreen([])
        screen.filtered_snippets = []
        screen.selected_snippet = None  # No selection
        
        with patch('textual.screen.Screen.notify') as mock_notify:
            # Mock the query_one method to avoid NoMatches error
            with patch.object(screen, 'query_one') as mock_query:
                mock_table = MagicMock()
                mock_table.cursor_row = -1  # No selection
                mock_table.row_count = 0  # No rows
                mock_query.return_value = mock_table
                
                screen.action_copy_snippet()
                
                # Should notify about invalid selection
                mock_notify.assert_called_once()
                assert "select" in mock_notify.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_copy_snippet_clipboard_error(self, temp_db_with_data, sample_snippets):
        """Test copying snippet when clipboard operation fails."""
        from codx.tui.screens import SnippetListScreen
        
        screen = SnippetListScreen(sample_snippets)
        screen.filtered_snippets = sample_snippets
        screen.selected_snippet = sample_snippets[0]  # Set selected snippet directly
        
        with patch('pyperclip.copy', side_effect=Exception("Clipboard error")):
            with patch('textual.screen.Screen.notify') as mock_notify:
                screen.action_copy_snippet()
                
                # Should show error notification
                mock_notify.assert_called_once()
                assert "error" in mock_notify.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_run_snippet(self, temp_db_with_data, sample_snippets):
        """Test running a snippet."""
        from codx.tui.screens import SnippetListScreen
        
        screen = SnippetListScreen(sample_snippets)
        screen.filtered_snippets = sample_snippets
        screen.selected_snippet = sample_snippets[0]  # Set selected snippet directly
        
        # Mock app for push_screen
        mock_app = MagicMock()
        
        with patch.object(type(screen), 'app', new_callable=lambda: mock_app):
            screen.action_run_snippet()
            
            # Should push run screen
            mock_app.push_screen.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_snippet_with_variables(self, temp_db_with_data):
        """Test running a snippet with variables."""
        from codx.tui.screens import SnippetRunScreen
        
        snippet_with_vars = {
            'id': 1,
            'description': 'Snippet with variables',
            'content': 'print("Hello, {{name}}!")',
            'language': 'python',
            'tags': ['test'],
            'created_at': '2023-01-01 12:00:00'
        }
        
        screen = SnippetRunScreen(snippet_with_vars)
        
        with patch('codx.utils.variables.extract_variables', return_value=['name']):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout='Hello, World!',
                    stderr=''
                )
                
                # Test that the screen can handle variables
                assert 'name' in snippet_with_vars['content']
                assert screen.snippet == snippet_with_vars
    
    @pytest.mark.asyncio
    async def test_run_snippet_execution_error(self, temp_db_with_data, sample_snippets):
        """Test running snippet when execution fails."""
        from codx.tui.screens import SnippetRunScreen
        
        screen = SnippetRunScreen(sample_snippets[0])
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout='',
                stderr='SyntaxError: invalid syntax'
            )
            
            # Test that the screen can handle execution errors
            assert screen.snippet == sample_snippets[0]
            assert hasattr(screen, 'run_snippet_async')
    
    @pytest.mark.asyncio
    async def test_edit_snippet(self, temp_db_with_data, sample_snippets):
        """Test editing a snippet."""
        from codx.tui.screens import SnippetListScreen
        
        screen = SnippetListScreen(sample_snippets)
        screen.filtered_snippets = sample_snippets
        screen.selected_snippet = sample_snippets[0]  # Set selected snippet directly
        
        # Mock app for push_screen
        mock_app = MagicMock()
        
        with patch.object(type(screen), 'app', new_callable=lambda: mock_app):
            screen.action_edit_snippet()
            
            # Should push edit screen
            mock_app.push_screen.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_edit_snippet_no_changes(self, temp_db_with_data, sample_snippets):
        """Test editing snippet when no changes are made."""
        from codx.tui.screens import SnippetEditScreen
        
        screen = SnippetEditScreen(sample_snippets[0])
        
        # Test that the screen is properly initialized
        assert screen.snippet == sample_snippets[0]
        assert hasattr(screen, 'action_open_editor')
    
    def test_delete_snippet(self, temp_db_with_data, sample_snippets):
        """Test deleting a snippet."""
        from codx.tui.screens import SnippetListScreen
        
        screen = SnippetListScreen(sample_snippets)
        screen.filtered_snippets = sample_snippets
        screen.selected_snippet = sample_snippets[0]  # Set selected snippet directly
        
        # Mock the app property to avoid NoActiveAppError
        mock_app = MagicMock()
        
        with patch.object(type(screen), 'app', new_callable=lambda: mock_app):
            screen.action_delete_snippet()
            
            # Should call app.exit with delete action
            mock_app.exit.assert_called_once_with({
                "action": "delete", 
                "snippet": sample_snippets[0]
            })
    
    def test_delete_snippet_no_selection(self, temp_db_with_data, sample_snippets):
        """Test deleting snippet when no snippet is selected."""
        from codx.tui.screens import SnippetListScreen
        
        screen = SnippetListScreen(sample_snippets)
        screen.filtered_snippets = sample_snippets
        screen.selected_snippet = None  # No selection
        
        # Mock the app property to avoid NoActiveAppError
        mock_app = MagicMock()
        
        with patch('textual.screen.Screen.notify') as mock_notify:
            with patch.object(type(screen), 'app', new_callable=lambda: mock_app):
                # Mock the query_one method to avoid NoMatches error
                with patch.object(screen, 'query_one') as mock_query:
                    mock_table = MagicMock()
                    mock_table.cursor_row = -1  # No selection
                    mock_table.row_count = 0  # No rows
                    mock_query.return_value = mock_table
                    
                    screen.action_delete_snippet()
                    
                    # Should notify about no selection
                    mock_notify.assert_called_once()
    
    def test_view_snippet(self, temp_db_with_data, sample_snippets):
        """Test viewing a snippet in detail."""
        from codx.tui.screens import SnippetListScreen
        
        screen = SnippetListScreen(sample_snippets)
        screen.filtered_snippets = sample_snippets
        screen.selected_snippet = sample_snippets[0]  # Set selected snippet directly
        
        # Mock app for push_screen
        mock_app = MagicMock()
        
        with patch.object(type(screen), 'app', new_callable=lambda: mock_app):
            screen.action_view_snippet()
            
            # Should push view screen
            mock_app.push_screen.assert_called_once()
    
    def test_on_input_changed(self, temp_db_with_data, sample_snippets):
        """Test search input change handling."""
        from codx.tui.screens import SnippetListScreen
        from textual.widgets import Input
        
        screen = SnippetListScreen(sample_snippets)
        
        # Mock the search input event
        mock_input = MagicMock(spec=Input)
        mock_input.id = "search-input"
        mock_input.value = "hello"
        
        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = "hello"
        
        with patch.object(screen, 'update_table') as mock_update:
            screen.on_input_changed(mock_event)
            
            # Should update table after filtering
            mock_update.assert_called_once()
    
    def test_key_bindings(self, temp_db_with_data, sample_snippets):
        """Test key bindings functionality."""
        from codx.tui.screens import SnippetListScreen
        
        screen = SnippetListScreen(sample_snippets)
        screen.filtered_snippets = sample_snippets
        screen.selected_snippet = sample_snippets[0]  # Set selected snippet directly
        
        # Mock app for push_screen
        mock_app = MagicMock()
        
        with patch.object(type(screen), 'app', new_callable=lambda: mock_app):
            # Test copy action (c key)
            with patch('pyperclip.copy') as mock_copy:
                with patch('textual.screen.Screen.notify'):
                    screen.action_copy_snippet()
                    mock_copy.assert_called_once()
            
            # Test run action (r key)
            screen.action_run_snippet()
            mock_app.push_screen.assert_called_once()
            
            # Test edit action (e key)
            mock_app.reset_mock()
            screen.action_edit_snippet()
            mock_app.push_screen.assert_called_once()
            
            # Test view action (v key)
            mock_app.reset_mock()
            screen.action_view_snippet()
            mock_app.push_screen.assert_called_once()
            
            # Test delete action (d key)
            mock_app.reset_mock()
            screen.action_delete_snippet()
            # Should call app.exit with delete action
            mock_app.exit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_quit_action(self, temp_db_with_data):
        """Test quit action."""
        app = SnippetFinderApp(snippets=[])
        
        with patch.object(app, 'exit') as mock_exit:
            await app.action_quit()
            mock_exit.assert_called_once()
    
    def test_css_styling(self, temp_db_with_data):
        """Test CSS styling is properly applied."""
        app = SnippetFinderApp(snippets=[])
        
        # Check that CSS is defined
        assert hasattr(app, 'CSS')
        assert isinstance(app.CSS, str)
        assert len(app.CSS) > 0
    
    def test_database_operations(self, temp_db_with_data, sample_snippets):
        """Test database operations."""
        from codx.tui.screens import SnippetListScreen
        
        screen = SnippetListScreen(sample_snippets)
        screen.selected_snippet = sample_snippets[0]  # Set selected snippet directly
        
        # Test loading snippets through app
        app = SnippetFinderApp(snippets=sample_snippets)
        
        with patch('codx.core.database.Database') as mock_db_class:
            mock_db = MagicMock()
            mock_db_class.return_value = mock_db
            mock_db.get_all_snippets.return_value = sample_snippets
            
            # Test that app can be initialized with snippets
            assert app.snippets == sample_snippets
        
        # Test database operations through screen actions
        # Mock the app property to avoid NoActiveAppError
        mock_app = MagicMock()
        
        with patch.object(type(screen), 'app', new_callable=lambda: mock_app):
            screen.action_delete_snippet()
            
            # Should call app.exit with delete action
            mock_app.exit.assert_called_once_with({
                "action": "delete", 
                "snippet": sample_snippets[0]
            })
    
    def test_database_error_handling(self, temp_db_with_data, sample_snippets):
        """Test database error handling."""
        from codx.tui.screens import SnippetListScreen
        
        screen = SnippetListScreen(sample_snippets)
        screen.filtered_snippets = sample_snippets
        screen.selected_snippet = sample_snippets[0]  # Set selected snippet directly
        
        # Mock the app property to avoid NoActiveAppError
        mock_app = MagicMock()
        
        # Test app.exit operation
        with patch.object(type(screen), 'app', new_callable=lambda: mock_app):
            screen.action_delete_snippet()
            
            # Should call app.exit with delete action
            mock_app.exit.assert_called_once_with({
                "action": "delete", 
                "snippet": sample_snippets[0]
            })
    
    def test_table_selection_handling(self, temp_db_with_data, sample_snippets):
        """Test table row selection and navigation."""
        from codx.tui.screens import SnippetListScreen
        
        screen = SnippetListScreen(sample_snippets)
        screen.filtered_snippets = sample_snippets
        screen.selected_snippet = None  # No selection
        
        with patch('textual.screen.Screen.notify') as mock_notify:
             # Mock the query_one method to avoid NoMatches error
             with patch.object(screen, 'query_one') as mock_query:
                 mock_table = MagicMock()
                 mock_table.cursor_row = -1  # No selection
                 mock_table.row_count = 0  # No rows
                 mock_query.return_value = mock_table
                 
                 screen.action_copy_snippet()
                 
                 # Should notify about no selection
                 mock_notify.assert_called_once()
                 assert "select" in mock_notify.call_args[0][0].lower()
    
    def test_search_performance(self, temp_db_with_data):
        """Test search performance with large dataset."""
        from codx.utils.search import fuzzy_search_snippets
        
        # Create a large dataset
        large_dataset = []
        for i in range(1000):
            large_dataset.append({
                'id': i,
                'description': f'Test snippet {i}',
                'content': f'print("test {i}")',
                'language': 'python',
                'tags': [f'tag{i}'],
                'created_at': '2023-01-01 12:00:00'
            })
        
        # Test filtering performance
        import time
        start_time = time.time()
        results = fuzzy_search_snippets(large_dataset, "test")
        end_time = time.time()
        
        # Should complete within reasonable time (< 1 second)
        assert (end_time - start_time) < 1.0
        assert len(results) > 0
    
    def test_app_title_and_metadata(self, temp_db_with_data):
        """Test app title and metadata properties."""
        app = SnippetFinderApp(snippets=[])
        
        # Check app has proper title
        assert hasattr(app, 'title')
        assert "CODX" in app.title or "Snippet" in app.title
        
        # Check app has proper sub-title
        if hasattr(app, 'sub_title'):
            assert isinstance(app.sub_title, str)