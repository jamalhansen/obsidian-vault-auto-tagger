from obsidian_vault_auto_tagger.prompts import build_system_prompt

def test_build_system_prompt_includes_tags():
    existing_tags = ["python", "sql", "data-science"]
    prompt = build_system_prompt(existing_tags)
    
    assert "python" in prompt
    assert "sql" in prompt
    assert "data-science" in prompt
    assert "EXISTING TAGS IN VAULT" in prompt
