"""Tests for the database module."""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

from codx.core.database import Database


class TestDatabase:
    """Test cases for the Database class."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        db = Database(db_path)
        db.initialize_database()
        yield db
        
        db.close()
        try:
            os.unlink(db_path)
        except OSError:
            pass
    
    @pytest.fixture
    def sample_snippets(self):
        """Sample snippet data for testing."""
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
            }
        ]
    
    def test_database_initialization(self):
        """Test database initialization with schema."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = Database(db_path)
            db.initialize_database()
            
            # Check if tables exist
            cursor = db.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            assert 'snippets' in tables
            assert 'tags' in tables
            assert 'snippet_tags' in tables
            
            # Check snippets table structure
            cursor.execute("PRAGMA table_info(snippets);")
            columns = [row[1] for row in cursor.fetchall()]
            expected_columns = ['id', 'description', 'content', 'language', 'created_at', 'updated_at']
            for col in expected_columns:
                assert col in columns
            
            db.close()
        finally:
            try:
                os.unlink(db_path)
            except OSError:
                pass
    
    def test_database_initialization_with_missing_schema(self):
        """Test database initialization when schema file is missing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = Database(db_path)
            
            # Mock the schema file to not exist
            with patch('pathlib.Path.exists', return_value=False):
                with pytest.raises(FileNotFoundError):
                    db.initialize_database()
            
            db.close()
        finally:
            try:
                os.unlink(db_path)
            except OSError:
                pass
    
    def test_add_snippet_basic(self, temp_db):
        """Test adding a basic snippet."""
        snippet_id = temp_db.add_snippet(
            description="Test snippet",
            content="print('test')",
            language="python",
            tags=["test"]
        )
        
        assert snippet_id is not None
        assert isinstance(snippet_id, int)
        assert snippet_id > 0
    
    def test_add_snippet_without_tags(self, temp_db):
        """Test adding a snippet without tags."""
        snippet_id = temp_db.add_snippet(
            description="Test snippet",
            content="print('test')",
            language="python",
            tags=[]
        )
        
        assert snippet_id is not None
        
        # Verify snippet was added
        snippet = temp_db.get_snippet_by_id(snippet_id)
        assert snippet is not None
        assert snippet['description'] == "Test snippet"
        assert snippet['tags'] == []
    
    def test_add_snippet_empty_tags(self, temp_db):
        """Test adding a snippet with empty tags list."""
        snippet_id = temp_db.add_snippet(
            description="Test snippet",
            content="print('test')",
            language="python",
            tags=None
        )
        
        assert snippet_id is not None
        snippet = temp_db.get_snippet_by_id(snippet_id)
        assert snippet['tags'] == []
    
    def test_add_multiple_snippets(self, temp_db, sample_snippets):
        """Test adding multiple snippets."""
        snippet_ids = []
        for snippet_data in sample_snippets:
            snippet_id = temp_db.add_snippet(**snippet_data)
            snippet_ids.append(snippet_id)
        
        assert len(snippet_ids) == len(sample_snippets)
        assert all(isinstance(sid, int) for sid in snippet_ids)
        assert len(set(snippet_ids)) == len(snippet_ids)  # All unique
    
    def test_get_snippet_by_id(self, temp_db):
        """Test retrieving a snippet by ID."""
        # Add a snippet first
        snippet_id = temp_db.add_snippet(
            description="Test snippet",
            content="print('hello')",
            language="python",
            tags=["test", "python"]
        )
        
        # Retrieve the snippet
        snippet = temp_db.get_snippet_by_id(snippet_id)
        
        assert snippet is not None
        assert snippet['id'] == snippet_id
        assert snippet['description'] == "Test snippet"
        assert snippet['content'] == "print('hello')"
        assert snippet['language'] == "python"
        assert set(snippet['tags']) == {"test", "python"}
        assert 'created_at' in snippet
        assert 'updated_at' in snippet
    
    def test_get_snippet_by_nonexistent_id(self, temp_db):
        """Test retrieving a snippet with non-existent ID."""
        snippet = temp_db.get_snippet_by_id(999)
        assert snippet is None
    
    def test_get_all_snippets_empty(self, temp_db):
        """Test getting all snippets when database is empty."""
        snippets = temp_db.get_all_snippets()
        assert snippets == []
    
    def test_get_all_snippets(self, temp_db, sample_snippets):
        """Test getting all snippets."""
        # Add sample snippets
        added_ids = []
        for snippet_data in sample_snippets:
            snippet_id = temp_db.add_snippet(**snippet_data)
            added_ids.append(snippet_id)
        
        # Get all snippets
        snippets = temp_db.get_all_snippets()
        
        assert len(snippets) == len(sample_snippets)
        
        # Check that all added snippets are present
        retrieved_ids = [s['id'] for s in snippets]
        assert set(retrieved_ids) == set(added_ids)
        
        # Check content of first snippet
        first_snippet = next(s for s in snippets if s['description'] == 'Python Hello World')
        assert first_snippet['language'] == 'python'
        assert 'python' in first_snippet['tags']
        assert 'basic' in first_snippet['tags']
    
    def test_update_snippet(self, temp_db):
        """Test updating a snippet."""
        # Add a snippet first
        snippet_id = temp_db.add_snippet(
            description="Original description",
            content="print('original')",
            language="python",
            tags=["original"]
        )
        
        # Update the snippet
        success = temp_db.update_snippet(
            snippet_id=snippet_id,
            description="Updated description",
            content="print('updated')",
            language="python3",
            tags=["updated", "new"]
        )
        
        assert success is True
        
        # Verify the update
        updated_snippet = temp_db.get_snippet_by_id(snippet_id)
        assert updated_snippet['description'] == "Updated description"
        assert updated_snippet['content'] == "print('updated')"
        assert updated_snippet['language'] == "python3"
        assert set(updated_snippet['tags']) == {"updated", "new"}
    
    def test_update_snippet_remove_tags(self, temp_db):
        """Test updating a snippet to remove all tags."""
        # Add a snippet with tags
        snippet_id = temp_db.add_snippet(
            description="Test snippet",
            content="print('test')",
            language="python",
            tags=["tag1", "tag2"]
        )
        
        # Update to remove all tags
        success = temp_db.update_snippet(
            snippet_id=snippet_id,
            description="Test snippet",
            content="print('test')",
            language="python",
            tags=[]
        )
        
        assert success is True
        
        # Verify tags were removed
        updated_snippet = temp_db.get_snippet_by_id(snippet_id)
        assert updated_snippet['tags'] == []
    
    def test_update_nonexistent_snippet(self, temp_db):
        """Test updating a non-existent snippet."""
        success = temp_db.update_snippet(
            snippet_id=999,
            description="Updated description",
            content="print('updated')",
            language="python",
            tags=["updated"]
        )
        
        assert success is False
    
    def test_delete_snippet(self, temp_db):
        """Test deleting a snippet."""
        # Add a snippet first
        snippet_id = temp_db.add_snippet(
            description="To be deleted",
            content="print('delete me')",
            language="python",
            tags=["delete"]
        )
        
        # Verify it exists
        assert temp_db.get_snippet_by_id(snippet_id) is not None
        
        # Delete the snippet
        success = temp_db.delete_snippet(snippet_id)
        assert success is True
        
        # Verify it's gone
        assert temp_db.get_snippet_by_id(snippet_id) is None
    
    def test_delete_nonexistent_snippet(self, temp_db):
        """Test deleting a non-existent snippet."""
        success = temp_db.delete_snippet(999)
        assert success is False
    
    def test_database_connection_error(self):
        """Test database connection error handling."""
        # Try to create database in non-existent directory
        invalid_path = "/non/existent/path/test.db"
        
        with pytest.raises(Exception):
            db = Database(invalid_path)
            db.initialize_database()
    
    def test_database_close(self, temp_db):
        """Test database connection closing."""
        temp_db.close()
        
        # Trying to use closed database should raise an error
        with pytest.raises(sqlite3.ProgrammingError):
            temp_db.get_all_snippets()
    
    def test_tag_management(self, temp_db):
        """Test tag management functionality."""
        # Add snippets with various tags
        temp_db.add_snippet(
            description="Python snippet",
            content="print('python')",
            language="python",
            tags=["python", "basic", "tutorial"]
        )
        
        temp_db.add_snippet(
            description="JavaScript snippet",
            content="console.log('js')",
            language="javascript",
            tags=["javascript", "basic", "web"]
        )
        
        # Get all snippets and check tag handling
        snippets = temp_db.get_all_snippets()
        
        python_snippet = next(s for s in snippets if s['language'] == 'python')
        js_snippet = next(s for s in snippets if s['language'] == 'javascript')
        
        assert set(python_snippet['tags']) == {"python", "basic", "tutorial"}
        assert set(js_snippet['tags']) == {"javascript", "basic", "web"}
    
    def test_special_characters_in_content(self, temp_db):
        """Test handling special characters in snippet content."""
        special_content = "print('Hello, \"World\"!\n\tTabbed line')"
        
        snippet_id = temp_db.add_snippet(
            description="Special characters test",
            content=special_content,
            language="python",
            tags=["test"]
        )
        
        retrieved_snippet = temp_db.get_snippet_by_id(snippet_id)
        assert retrieved_snippet['content'] == special_content
    
    def test_unicode_content(self, temp_db):
        """Test handling Unicode content."""
        unicode_content = "print('Hello, 世界! 🌍')"
        
        snippet_id = temp_db.add_snippet(
            description="Unicode test",
            content=unicode_content,
            language="python",
            tags=["unicode", "test"]
        )
        
        retrieved_snippet = temp_db.get_snippet_by_id(snippet_id)
        assert retrieved_snippet['content'] == unicode_content
    
    def test_large_content(self, temp_db):
        """Test handling large content."""
        # Create a large snippet (1000+ lines)
        large_content = "\n".join([f"print('Line {i}')" for i in range(1001)])
        
        snippet_id = temp_db.add_snippet(
            description="Large content test",
            content=large_content,
            language="python",
            tags=["large", "test"]
        )
        
        retrieved_snippet = temp_db.get_snippet_by_id(snippet_id)
        assert retrieved_snippet['content'] == large_content
        assert len(retrieved_snippet['content'].splitlines()) > 1000