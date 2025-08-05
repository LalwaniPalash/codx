"""Shared test fixtures and configuration for codx tests."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from codx.core.database import Database


@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def temp_db_path():
    """Create a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    yield db_path
    
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def clean_database(temp_db_path):
    """Create a clean, initialized database for testing."""
    db = Database(temp_db_path)
    db.initialize_database()
    yield db
    db.close()


@pytest.fixture
def sample_snippet_data():
    """Standard sample snippet data for testing."""
    return {
        'description': 'Test Python snippet',
        'content': 'print("Hello, World!")',
        'language': 'python',
        'tags': ['python', 'test', 'hello']
    }


@pytest.fixture
def multiple_sample_snippets():
    """Multiple sample snippets for testing."""
    return [
        {
            'description': 'Python Hello World',
            'content': 'print("Hello, World!")',
            'language': 'python',
            'tags': ['python', 'basic']
        },
        {
            'description': 'JavaScript Function',
            'content': 'function greet(name) { return `Hello, ${name}!`; }',
            'language': 'javascript',
            'tags': ['javascript', 'function']
        },
        {
            'description': 'Bash Script',
            'content': '#!/bin/bash\necho "Hello from bash"',
            'language': 'bash',
            'tags': ['bash', 'script']
        },
        {
            'description': 'SQL Query',
            'content': 'SELECT * FROM users WHERE active = 1;',
            'language': 'sql',
            'tags': ['sql', 'database']
        },
        {
            'description': 'CSS Styling',
            'content': '.container { display: flex; justify-content: center; }',
            'language': 'css',
            'tags': ['css', 'styling']
        }
    ]


@pytest.fixture
def populated_database(clean_database, multiple_sample_snippets):
    """Database populated with sample snippets."""
    snippet_ids = []
    for snippet in multiple_sample_snippets:
        snippet_id = clean_database.add_snippet(**snippet)
        snippet_ids.append(snippet_id)
    
    return {
        'database': clean_database,
        'snippet_ids': snippet_ids,
        'snippets': multiple_sample_snippets
    }


@pytest.fixture
def mock_db_path(temp_db_path):
    """Mock the get_db_path function to return a temporary path."""
    with patch('codx.cli.commands.get_db_path', return_value=temp_db_path):
        with patch('codx.tui.app.get_db_path', return_value=temp_db_path):
            yield temp_db_path


@pytest.fixture
def temp_file_content():
    """Create a temporary file with content for testing."""
    content = "print('Hello from file')"
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
        tmp.write(content)
        file_path = tmp.name
    
    yield file_path, content
    
    try:
        os.unlink(file_path)
    except OSError:
        pass


@pytest.fixture
def mock_clipboard():
    """Mock clipboard operations."""
    with patch('pyperclip.copy') as mock_copy:
        with patch('pyperclip.paste', return_value='mocked clipboard content') as mock_paste:
            yield {
                'copy': mock_copy,
                'paste': mock_paste
            }


@pytest.fixture
def mock_subprocess():
    """Mock subprocess operations."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Mock output"
        mock_run.return_value.stderr = ""
        yield mock_run


@pytest.fixture
def mock_editor():
    """Mock editor operations."""
    with patch('codx.utils.helpers.open_editor_for_content') as mock_editor:
        mock_editor.return_value = "print('edited content')"
        yield mock_editor


@pytest.fixture
def mock_user_input():
    """Mock user input for interactive prompts."""
    with patch('builtins.input') as mock_input:
        yield mock_input


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables before each test."""
    # Store original environment
    original_env = os.environ.copy()
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def snippet_with_variables():
    """Sample snippet containing variables for testing."""
    return {
        'description': 'Snippet with variables',
        'content': 'print("Hello, {{name}}! You are {{age}} years old.")',
        'language': 'python',
        'tags': ['python', 'variables', 'test']
    }


@pytest.fixture
def large_content_snippet():
    """Sample snippet with large content for testing."""
    # Generate a large snippet (1000+ lines)
    large_content = "\n".join([f"print('Line {i}')" for i in range(1001)])
    
    return {
        'description': 'Large content snippet',
        'content': large_content,
        'language': 'python',
        'tags': ['python', 'large', 'test']
    }


@pytest.fixture
def unicode_snippet():
    """Sample snippet with Unicode content for testing."""
    return {
        'description': 'Unicode test snippet',
        'content': 'print("Hello, 世界! 🌍 Здравствуй мир!")',
        'language': 'python',
        'tags': ['python', 'unicode', 'international']
    }


@pytest.fixture
def special_chars_snippet():
    """Sample snippet with special characters for testing."""
    return {
        'description': 'Special characters test',
        'content': 'print(\'Hello, \"World\"!\\n\\tTabbed line\')',
        'language': 'python',
        'tags': ['python', 'special-chars', 'test']
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "asyncio: marks tests as async"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "cli: marks tests as CLI tests"
    )
    config.addinivalue_line(
        "markers", "tui: marks tests as TUI tests"
    )
    config.addinivalue_line(
        "markers", "database: marks tests as database tests"
    )
    config.addinivalue_line(
        "markers", "utils: marks tests as utility function tests"
    )


# Custom pytest collection
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file names."""
    for item in items:
        # Add markers based on test file names
        if "test_cli" in item.nodeid:
            item.add_marker(pytest.mark.cli)
        elif "test_tui" in item.nodeid:
            item.add_marker(pytest.mark.tui)
        elif "test_database" in item.nodeid:
            item.add_marker(pytest.mark.database)
        elif "test_utils" in item.nodeid:
            item.add_marker(pytest.mark.utils)
        
        # Add integration marker for tests that use multiple components
        if any(keyword in item.nodeid for keyword in ["integration", "end_to_end", "e2e"]):
            item.add_marker(pytest.mark.integration)
        
        # Add slow marker for tests that might take longer
        if any(keyword in item.nodeid for keyword in ["large", "performance", "stress"]):
            item.add_marker(pytest.mark.slow)