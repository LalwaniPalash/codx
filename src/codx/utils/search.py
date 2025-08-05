"""Search utilities for CODX."""

from typing import List, Dict, Optional
from fuzzywuzzy import fuzz, process
from ..core.database import Database


def search_snippets(query: str, limit: int = 50, language: str = None, tags: List[str] = None, 
                   use_fuzzy: bool = True, db: Optional[Database] = None) -> List[dict]:
    """Search snippets using FTS5 with optional fuzzy search enhancement.
    
    Args:
        query: Search query
        limit: Maximum number of results to return
        language: Filter by programming language
        tags: Filter by tags (must contain all specified tags)
        use_fuzzy: Whether to apply fuzzy search on top of FTS5 results
        db: Database instance (will create new one if not provided)
        
    Returns:
        List of matching snippets sorted by relevance
    """
    # Initialize database if not provided
    if db is None:
        db = Database()
        should_close = True
    else:
        should_close = False
    
    try:
        # If no query, return all snippets with filters
        if not query.strip():
            snippets = db.get_all_snippets()
            return _apply_filters(snippets, language, tags)[:limit]
        
        # Use FTS5 search as primary method
        fts_results = db.search_snippets_fts(query, limit * 2)  # Get more results for filtering
        
        # Apply additional filters
        filtered_results = _apply_filters(fts_results, language, tags)
        
        # Apply fuzzy search enhancement if requested
        if use_fuzzy and filtered_results:
            enhanced_results = _enhance_with_fuzzy_search(filtered_results, query, limit)
            return enhanced_results
        
        return filtered_results[:limit]
        
    finally:
        if should_close:
            db.close()


def fuzzy_search_snippets(snippets: List[dict], query: str, limit: int = 10, 
                         language: str = None, tags: List[str] = None) -> List[dict]:
    """Legacy fuzzy search function for backward compatibility.
    
    Args:
        snippets: List of snippet dictionaries
        query: Search query
        limit: Maximum number of results to return
        language: Filter by programming language
        tags: Filter by tags (must contain all specified tags)
        
    Returns:
        List of matching snippets sorted by relevance
    """
    # Apply filters first
    filtered_snippets = _apply_filters(snippets, language, tags)
    
    if not query.strip():
        return filtered_snippets[:limit]
    
    return _enhance_with_fuzzy_search(filtered_snippets, query, limit)


def _apply_filters(snippets: List[dict], language: str = None, tags: List[str] = None) -> List[dict]:
    """Apply language and tag filters to snippets.
    
    Args:
        snippets: List of snippet dictionaries
        language: Filter by programming language
        tags: Filter by tags (must contain all specified tags)
        
    Returns:
        Filtered list of snippets
    """
    filtered_snippets = snippets
    
    if language:
        filtered_snippets = [
            s for s in filtered_snippets 
            if s.get('language', '').lower() == language.lower()
        ]
    
    if tags:
        filtered_snippets = [
            s for s in filtered_snippets 
            if all(tag.lower() in [t.lower() for t in s.get('tags', [])] for tag in tags)
        ]
    
    return filtered_snippets


def _enhance_with_fuzzy_search(snippets: List[dict], query: str, limit: int) -> List[dict]:
    """Apply fuzzy search to enhance FTS5 results.
    
    Args:
        snippets: List of snippet dictionaries from FTS5 search
        query: Original search query
        limit: Maximum number of results to return
        
    Returns:
        Enhanced and re-ranked list of snippets
    """
    if not snippets:
        return []
    
    # Create searchable text for each snippet
    searchable_snippets = []
    for snippet in snippets:
        searchable_text = f"{snippet['description']} {snippet['content']} {snippet['language']} {' '.join(snippet['tags'])}"
        searchable_snippets.append((searchable_text, snippet))
    
    # Perform fuzzy search
    matches = process.extract(
        query,
        [text for text, _ in searchable_snippets],
        scorer=fuzz.partial_ratio,
        limit=limit
    )
    
    # Combine FTS5 rank with fuzzy score
    result = []
    for match_text, fuzzy_score in matches:
        if fuzzy_score > 60:  # Relevance threshold
            for text, snippet in searchable_snippets:
                if text == match_text:
                    # Combine FTS5 rank with fuzzy score for final ranking
                    fts_rank = snippet.get('rank', 0)
                    combined_score = (fuzzy_score * 0.7) + (fts_rank * 0.3) if fts_rank else fuzzy_score
                    snippet['_score'] = combined_score
                    snippet['_fuzzy_score'] = fuzzy_score
                    result.append(snippet)
                    break
    
    # Sort by combined score
    result.sort(key=lambda x: x.get('_score', 0), reverse=True)
    return result