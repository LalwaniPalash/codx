#!/usr/bin/env python3
"""
Database module for codx snippet library.
Handles database initialization and operations.
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional


class Database:
    """Database handler for the codx snippet library."""
    
    def __init__(self, db_path: str = None):
        """Initialize database connection.
        
        Args:
            db_path: Path to the SQLite database file
        """
        if db_path is None:
            # Default to ~/.codx/codx.db
            home_dir = Path.home()
            codx_dir = home_dir / ".codx"
            codx_dir.mkdir(exist_ok=True)
            db_path = str(codx_dir / "codx.db")
        
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self._closed = False
    
    def connect(self) -> sqlite3.Connection:
        """Establish database connection.
        
        Returns:
            SQLite connection object
        """
        if self._closed:
            raise sqlite3.ProgrammingError("Cannot operate on a closed database.")
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # Enable dict-like access
        return self.connection
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
        self._closed = True
    
    @property
    def conn(self) -> sqlite3.Connection:
        """Get database connection for backward compatibility."""
        return self.connect()
    
    def initialize_database(self):
        """Create database tables from schema.sql file."""
        schema_path = Path(__file__).parent / "schema.sql"
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
        with open(schema_path, 'r') as schema_file:
            schema_sql = schema_file.read()
        
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # Execute the entire schema as one script to handle multi-line statements
            cursor.executescript(schema_sql)
            
            conn.commit()
            print(f"Database initialized successfully at: {os.path.abspath(self.db_path)}")
            
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Failed to initialize database: {e}")
        finally:
            cursor.close()
    
    def get_all_snippets(self) -> list:
        """Retrieve all snippets with their tags.
        
        Returns:
            List of dictionaries containing snippet data
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # Get all snippets with their tags
            cursor.execute("""
                SELECT s.id, s.description, s.content, s.language, s.created_at, s.updated_at,
                       GROUP_CONCAT(t.name, ', ') as tags
                FROM snippets s
                LEFT JOIN snippet_tags st ON s.id = st.snippet_id
                LEFT JOIN tags t ON st.tag_id = t.id
                GROUP BY s.id
                ORDER BY s.created_at DESC
            """)
            
            rows = cursor.fetchall()
            snippets = []
            
            for row in rows:
                snippet = {
                    'id': row[0],
                    'description': row[1] or '',
                    'content': row[2],
                    'language': row[3] or '',
                    'created_at': row[4],
                    'updated_at': row[5],
                    'tags': row[6].split(', ') if row[6] else []
                }
                snippets.append(snippet)
            
            return snippets
            
        except sqlite3.Error as e:
            raise Exception(f"Failed to retrieve snippets: {e}")
        finally:
            cursor.close()
    
    def get_snippet_by_id(self, snippet_id: int) -> dict:
        """Retrieve a specific snippet by ID.
        
        Args:
            snippet_id: ID of the snippet to retrieve
            
        Returns:
            Dictionary containing snippet data
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT s.id, s.description, s.content, s.language, s.created_at, s.updated_at,
                       GROUP_CONCAT(t.name, ', ') as tags
                FROM snippets s
                LEFT JOIN snippet_tags st ON s.id = st.snippet_id
                LEFT JOIN tags t ON st.tag_id = t.id
                WHERE s.id = ?
                GROUP BY s.id
            """, (snippet_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            snippet = {
                'id': row[0],
                'description': row[1] or '',
                'content': row[2],
                'language': row[3] or '',
                'created_at': row[4],
                'updated_at': row[5],
                'tags': row[6].split(', ') if row[6] else []
            }
            
            return snippet
            
        except sqlite3.Error as e:
            raise Exception(f"Failed to retrieve snippet: {e}")
        finally:
            cursor.close()

    def add_snippet(self, description: str, content: str, language: str = None, tags: list = None) -> int:
        """Add a new snippet to the database.
        
        Args:
            description: Description of the snippet
            content: The actual code content
            language: Programming language
            tags: List of tag names
            
        Returns:
            ID of the created snippet
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # Insert snippet
            cursor.execute(
                "INSERT INTO snippets (description, content, language) VALUES (?, ?, ?)",
                (description, content, language)
            )
            snippet_id = cursor.lastrowid
            
            # Handle tags if provided
            if tags:
                for tag_name in tags:
                    tag_name = tag_name.strip().lower()
                    if not tag_name:
                        continue
                    
                    # Insert tag if it doesn't exist
                    cursor.execute(
                        "INSERT OR IGNORE INTO tags (name) VALUES (?)",
                        (tag_name,)
                    )
                    
                    # Get tag ID
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                    tag_id = cursor.fetchone()[0]
                    
                    # Link snippet and tag
                    cursor.execute(
                        "INSERT OR IGNORE INTO snippet_tags (snippet_id, tag_id) VALUES (?, ?)",
                        (snippet_id, tag_id)
                    )
            
            conn.commit()
            return snippet_id
            
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Failed to add snippet: {e}")
        finally:
            cursor.close()
    
    def update_snippet(self, snippet_id: int, description: str, content: str, language: str = None, tags: list = None) -> bool:
        """Update an existing snippet.
        
        Returns:
            True if update was successful, False if snippet not found
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # Check if snippet exists first
            cursor.execute("SELECT id FROM snippets WHERE id = ?", (snippet_id,))
            if not cursor.fetchone():
                return False
            
            # Update snippet
            cursor.execute(
                "UPDATE snippets SET description = ?, content = ?, language = ? WHERE id = ?",
                (description, content, language, snippet_id)
            )
            
            # Remove existing tags
            cursor.execute("DELETE FROM snippet_tags WHERE snippet_id = ?", (snippet_id,))
            
            # Add new tags
            if tags:
                for tag in tags:
                    tag = tag.strip().lower()
                    if not tag:
                        continue
                    
                    # Insert tag if it doesn't exist
                    cursor.execute(
                        "INSERT OR IGNORE INTO tags (name) VALUES (?)",
                        (tag,)
                    )
                    
                    # Get tag ID
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag,))
                    tag_id = cursor.fetchone()[0]
                    
                    # Link snippet to tag
                    cursor.execute(
                        "INSERT INTO snippet_tags (snippet_id, tag_id) VALUES (?, ?)",
                        (snippet_id, tag_id)
                    )
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Failed to update snippet: {e}")
        finally:
            cursor.close()
    
    def delete_snippet(self, snippet_id: int) -> bool:
        """Delete a snippet and its associated tags.
        
        Args:
            snippet_id: ID of the snippet to delete
            
        Returns:
            True if snippet was deleted, False if snippet not found
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # Check if snippet exists
            cursor.execute("SELECT id FROM snippets WHERE id = ?", (snippet_id,))
            if not cursor.fetchone():
                return False
            
            # Delete snippet-tag associations
            cursor.execute("DELETE FROM snippet_tags WHERE snippet_id = ?", (snippet_id,))
            
            # Delete the snippet
            cursor.execute("DELETE FROM snippets WHERE id = ?", (snippet_id,))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            conn.rollback()
            print(f"Failed to delete snippet: {e}")
            return False
        finally:
            cursor.close()
    
    def search_snippets_fts(self, query: str, limit: int = 50) -> list:
        """Search snippets using FTS5 full-text search.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of dictionaries containing snippet data with search rank
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # Prepare the FTS5 query - escape special characters and add wildcards
            fts_query = self._prepare_fts_query(query)
            
            # Search using FTS5 with ranking
            cursor.execute("""
                SELECT s.id, s.description, s.content, s.language, s.created_at, s.updated_at,
                       GROUP_CONCAT(t.name, ', ') as tags,
                       fts.rank
                FROM snippets_fts fts
                JOIN snippets s ON fts.content_id = s.id
                LEFT JOIN snippet_tags st ON s.id = st.snippet_id
                LEFT JOIN tags t ON st.tag_id = t.id
                WHERE snippets_fts MATCH ?
                GROUP BY s.id
                ORDER BY fts.rank
                LIMIT ?
            """, (fts_query, limit))
            
            rows = cursor.fetchall()
            snippets = []
            
            for row in rows:
                snippet = {
                    'id': row[0],
                    'description': row[1] or '',
                    'content': row[2],
                    'language': row[3] or '',
                    'created_at': row[4],
                    'updated_at': row[5],
                    'tags': row[6].split(', ') if row[6] else [],
                    'rank': row[7] if len(row) > 7 else 0
                }
                snippets.append(snippet)
            
            return snippets
            
        except sqlite3.Error as e:
            # Fallback to regular search if FTS5 fails
            print(f"FTS5 search failed, falling back to regular search: {e}")
            return self._fallback_search(query, limit)
        finally:
            cursor.close()
    
    def _prepare_fts_query(self, query: str) -> str:
        """Prepare a query string for FTS5 search.
        
        Args:
            query: Raw search query
            
        Returns:
            FTS5-formatted query string
        """
        # Remove special FTS5 characters that could cause syntax errors
        special_chars = ['"', "'", '(', ')', '*', ':', '^']
        cleaned_query = query
        for char in special_chars:
            cleaned_query = cleaned_query.replace(char, ' ')
        
        # Split into words and add prefix matching
        words = [word.strip() for word in cleaned_query.split() if word.strip()]
        if not words:
            return '""'  # Empty query
        
        # Create FTS5 query with prefix matching for each word
        fts_terms = []
        for word in words:
            if len(word) >= 2:  # Only add prefix matching for words with 2+ chars
                fts_terms.append(f'{word}*')
            else:
                fts_terms.append(word)
        
        return ' '.join(fts_terms)
    
    def _fallback_search(self, query: str, limit: int) -> list:
        """Fallback search method when FTS5 is not available.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of snippets matching the query
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # Simple LIKE-based search as fallback
            search_pattern = f"%{query}%"
            cursor.execute("""
                SELECT s.id, s.description, s.content, s.language, s.created_at, s.updated_at,
                       GROUP_CONCAT(t.name, ', ') as tags
                FROM snippets s
                LEFT JOIN snippet_tags st ON s.id = st.snippet_id
                LEFT JOIN tags t ON st.tag_id = t.id
                WHERE s.description LIKE ? OR s.content LIKE ? OR s.language LIKE ?
                GROUP BY s.id
                ORDER BY s.created_at DESC
                LIMIT ?
            """, (search_pattern, search_pattern, search_pattern, limit))
            
            rows = cursor.fetchall()
            snippets = []
            
            for row in rows:
                snippet = {
                    'id': row[0],
                    'description': row[1] or '',
                    'content': row[2],
                    'language': row[3] or '',
                    'created_at': row[4],
                    'updated_at': row[5],
                    'tags': row[6].split(', ') if row[6] else [],
                    'rank': 0  # No ranking for fallback search
                }
                snippets.append(snippet)
            
            return snippets
            
        except sqlite3.Error as e:
            raise Exception(f"Fallback search failed: {e}")
        finally:
            cursor.close()
    
    def populate_fts_table(self):
        """Populate the FTS5 table with existing snippet data.
        
        This method should be called after adding the FTS5 table to an existing database.
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # Clear existing FTS data
            cursor.execute("DELETE FROM snippets_fts")
            
            # Populate FTS table with existing snippets
            cursor.execute("""
                INSERT INTO snippets_fts(description, content, language, tags, content_id)
                SELECT 
                    s.description,
                    s.content,
                    s.language,
                    COALESCE(GROUP_CONCAT(t.name, ' '), '') as tags,
                    s.id
                FROM snippets s
                LEFT JOIN snippet_tags st ON s.id = st.snippet_id
                LEFT JOIN tags t ON st.tag_id = t.id
                GROUP BY s.id
            """)
            
            conn.commit()
            print("FTS5 table populated successfully")
            
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Failed to populate FTS table: {e}")
        finally:
            cursor.close()


def create_database():
    """Create and initialize the database."""
    db = Database()
    try:
        db.initialize_database()
    finally:
        db.close()


if __name__ == "__main__":
    create_database()