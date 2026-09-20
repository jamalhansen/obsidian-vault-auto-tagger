
from pydantic import BaseModel


class TagSuggestion(BaseModel):
    file_path: str
    existing_tags: list[str]
    suggested_tags: list[str]
    reasoning: str

class VaultTagReport(BaseModel):
    suggestions: list[TagSuggestion]
