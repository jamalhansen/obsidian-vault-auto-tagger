from typing import List

def build_system_prompt(existing_tags: List[str]) -> str:
    tags_list = ", ".join(existing_tags)
    return f"""You are an expert Obsidian vault librarian. Your goal is to suggest consistent, high-quality tags for a set of notes.

EXISTING TAGS IN VAULT:
{tags_list}

RULES:
1. PREFER EXISTING TAGS: If a note matches an existing tag concept, use the existing tag exactly.
2. NEW TAGS: Only suggest new tags if no existing tag fits. Use kebab-case for new tags.
3. SPECIFICITY: Tags should be specific enough to be useful but general enough to group related notes.
4. QUANTITY: Suggest 2-5 tags per note.
5. NO REDUNDANCY: Do not suggest tags that are already in the note.

OUTPUT FORMAT:
Return a JSON object with a list of suggestions. Each suggestion must include:
- file_path: The path provided for the note.
- existing_tags: The tags currently in the note.
- suggested_tags: ONLY the new tags you are suggesting (not ones already there).
- reasoning: Short explanation of why these tags were chosen.
"""

def build_user_prompt(notes_data: List[dict]) -> str:
    prompt = "Please suggest tags for the following notes:\n\n"
    for note in notes_data:
        prompt += f"FILE: {note['path']}\n"
        prompt += f"CONTENT:\n{note['content']}\n"
        prompt += f"CURRENT TAGS: {note['tags']}\n"
        prompt += "---\n"
    return prompt
