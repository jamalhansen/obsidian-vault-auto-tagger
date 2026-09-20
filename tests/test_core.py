"""Tests for core.apply_tag_suggestion -- the write-back step scan()'s own
docstring used to call "not implemented in this prototype" until now.
"""
import frontmatter

from obsidian_vault_auto_tagger.core import apply_tag_suggestion


def test_writes_suggested_tags_as_a_yaml_list(tmp_path):
    (tmp_path / "note.md").write_text("---\ntitle: A note\n---\nBody text.")

    ok = apply_tag_suggestion(tmp_path, "note.md", ["ai", "local-first"])

    assert ok is True
    post = frontmatter.load(tmp_path / "note.md")
    assert post.metadata["tags"] == ["ai", "local-first"]
    assert post.content.strip() == "Body text."


def test_merges_with_existing_tags_instead_of_overwriting(tmp_path):
    (tmp_path / "note.md").write_text("---\ntags:\n  - ai\n---\nBody.")

    apply_tag_suggestion(tmp_path, "note.md", ["ai", "llm"])

    post = frontmatter.load(tmp_path / "note.md")
    assert post.metadata["tags"] == ["ai", "llm"]  # union, not duplicated, order preserved


def test_handles_a_comma_separated_string_tags_field(tmp_path):
    """Real content sometimes stores tags as a single string rather than a
    YAML list (seen live in content-discovery-agent captures)."""
    (tmp_path / "note.md").write_text('---\ntags: "ai, safety"\n---\nBody.')

    apply_tag_suggestion(tmp_path, "note.md", ["llm"])

    post = frontmatter.load(tmp_path / "note.md")
    assert post.metadata["tags"] == ["ai", "safety", "llm"]


def test_missing_file_returns_false_not_raises(tmp_path):
    assert apply_tag_suggestion(tmp_path, "does-not-exist.md", ["ai"]) is False


def test_malformed_frontmatter_returns_false_not_raises(tmp_path):
    (tmp_path / "broken.md").write_text("---\ntags: [\n---\nBody.")
    assert apply_tag_suggestion(tmp_path, "broken.md", ["ai"]) is False
