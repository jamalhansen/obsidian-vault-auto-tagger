from typing import List
from pydantic import BaseModel

class TagSuggestion(BaseModel):
    file_path: str
    existing_tags: List[str]
    suggested_tags: List[str]
    reasoning: str

class VaultTagReport(BaseModel):
    suggestions: List[TagSuggestion]
