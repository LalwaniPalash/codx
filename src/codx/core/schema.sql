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

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE snippets_fts USING fts5(
    description,
    content,
    language,
    tags,
    content_id UNINDEXED
);

-- Trigger to update updated_at timestamp
CREATE TRIGGER update_snippet_timestamp 
    AFTER UPDATE ON snippets
    FOR EACH ROW
    BEGIN
        UPDATE snippets SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Triggers to keep FTS5 table in sync with snippets table
CREATE TRIGGER snippets_fts_insert
    AFTER INSERT ON snippets
    FOR EACH ROW
    BEGIN
        INSERT INTO snippets_fts(description, content, language, tags, content_id)
        VALUES (
            NEW.description,
            NEW.content,
            NEW.language,
            (SELECT GROUP_CONCAT(t.name, ' ') FROM tags t 
             JOIN snippet_tags st ON t.id = st.tag_id 
             WHERE st.snippet_id = NEW.id),
            NEW.id
        );
    END;

CREATE TRIGGER snippets_fts_update
    AFTER UPDATE ON snippets
    FOR EACH ROW
    BEGIN
        UPDATE snippets_fts SET
            description = NEW.description,
            content = NEW.content,
            language = NEW.language,
            tags = (SELECT GROUP_CONCAT(t.name, ' ') FROM tags t 
                   JOIN snippet_tags st ON t.id = st.tag_id 
                   WHERE st.snippet_id = NEW.id)
        WHERE content_id = NEW.id;
    END;

CREATE TRIGGER snippets_fts_delete
    AFTER DELETE ON snippets
    FOR EACH ROW
    BEGIN
        DELETE FROM snippets_fts WHERE content_id = OLD.id;
    END;

-- Trigger to update FTS when tags change
CREATE TRIGGER snippet_tags_fts_update
    AFTER INSERT ON snippet_tags
    FOR EACH ROW
    BEGIN
        UPDATE snippets_fts SET
            tags = (SELECT GROUP_CONCAT(t.name, ' ') FROM tags t 
                   JOIN snippet_tags st ON t.id = st.tag_id 
                   WHERE st.snippet_id = NEW.snippet_id)
        WHERE content_id = NEW.snippet_id;
    END;

CREATE TRIGGER snippet_tags_fts_delete
    AFTER DELETE ON snippet_tags
    FOR EACH ROW
    BEGIN
        UPDATE snippets_fts SET
            tags = (SELECT GROUP_CONCAT(t.name, ' ') FROM tags t 
                   JOIN snippet_tags st ON t.id = st.tag_id 
                   WHERE st.snippet_id = OLD.snippet_id)
        WHERE content_id = OLD.snippet_id;
    END;