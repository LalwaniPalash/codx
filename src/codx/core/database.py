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


def create_database():
    """Create and initialize the database."""
    db = Database()
    try:
        db.initialize_database()
    finally:
        db.close()


if __name__ == "__main__":
    create_database()