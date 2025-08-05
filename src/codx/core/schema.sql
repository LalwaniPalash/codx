-- Database schema for codx snippet library

-- Snippets table
CREATE TABLE snippets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT,
    content TEXT NOT NULL,
    language TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tags table
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

-- Junction table for many-to-many relationship between snippets and tags
CREATE TABLE snippet_tags (
    snippet_id INTEGER,
    tag_id INTEGER,
    PRIMARY KEY (snippet_id, tag_id),
    FOREIGN KEY (snippet_id) REFERENCES snippets(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX idx_snippets_language ON snippets(language);
CREATE INDEX idx_snippets_created_at ON snippets(created_at);
CREATE INDEX idx_tags_name ON tags(name);

-- Trigger to update updated_at timestamp
CREATE TRIGGER update_snippet_timestamp 
    AFTER UPDATE ON snippets
    FOR EACH ROW
    BEGIN
        UPDATE snippets SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;