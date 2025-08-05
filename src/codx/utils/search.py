"""Search utilities for CODX."""

from typing import List, Dict
from fuzzywuzzy import fuzz, process


def fuzzy_search_snippets(snippets: List[dict], query: str, limit: int = 10, language: str = None, tags: List[str] = None) -> List[dict]:
    """Perform fuzzy search on snippets.
    
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
    filtered_snippets = snippets
    
    if language:
        filtered_snippets = [s for s in filtered_snippets if s.get('language', '').lower() == language.lower()]
    
    if tags:
        filtered_snippets = [
            s for s in filtered_snippets 
            if all(tag.lower() in [t.lower() for t in s.get('tags', [])] for tag in tags)
        ]
    
    if not query.strip():
        return filtered_snippets[:limit]
    
    # Create searchable text for each snippet
    searchable_snippets = []
    for snippet in filtered_snippets:
        searchable_text = f"{snippet['description']} {snippet['content']} {snippet['language']} {' '.join(snippet['tags'])}"
        searchable_snippets.append((searchable_text, snippet))
    
    if not searchable_snippets:
        return []
    
    # Perform fuzzy search
    matches = process.extract(
        query,
        [text for text, _ in searchable_snippets],
        scorer=fuzz.partial_ratio,
        limit=limit
    )
    
    # Return matched snippets
    result = []
    for match_text, score in matches:
        if score > 60:  # Improved relevance threshold for better results
            for text, snippet in searchable_snippets:
                if text == match_text:
                    snippet['_score'] = score
                    result.append(snippet)
                    break
    
    return result