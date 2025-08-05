"""Data models for CODX."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Snippet:
    """Represents a code snippet."""
    
    id: Optional[int] = None
    description: str = ""
    content: str = ""
    language: str = ""
    tags: str = ""
    
    @property
    def tag_list(self) -> List[str]:
        """Return tags as a list."""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]
    
    def __str__(self) -> str:
        return f"Snippet({self.id}): {self.description}"
    
    def __repr__(self) -> str:
        return f"Snippet(id={self.id}, description='{self.description}', language='{self.language}')"