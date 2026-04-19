"""Tests for obsidian_vault_auto_tagger.logic utilities."""
from obsidian_vault_auto_tagger.logic import get_all_vault_tags, VaultTaggerError, ProviderSetupError, LLMRunError


class TestTypedErrors:
    def test_vault_tagger_error_is_base(self):
        assert issubclass(ProviderSetupError, VaultTaggerError)
        assert issubclass(LLMRunError, VaultTaggerError)

    def test_provider_setup_error_is_exception(self):
        err = ProviderSetupError("bad provider")
        assert isinstance(err, Exception)
        assert "bad provider" in str(err)

    def test_llm_run_error_is_exception(self):
        err = LLMRunError("run failed")
        assert isinstance(err, Exception)
        assert "run failed" in str(err)


class TestGetAllVaultTags:
    def test_collects_list_tags(self, tmp_path):
        (tmp_path / "note.md").write_text("---\ntags:\n  - ai\n  - python\n---\nContent")
        tags = get_all_vault_tags(tmp_path)
        assert "ai" in tags
        assert "python" in tags

    def test_collects_string_tag(self, tmp_path):
        (tmp_path / "note.md").write_text("---\ntags: ai\n---\nContent")
        tags = get_all_vault_tags(tmp_path)
        assert "ai" in tags

    def test_skips_notes_without_tags(self, tmp_path):
        (tmp_path / "note.md").write_text("---\ntitle: No tags\n---\nContent")
        assert get_all_vault_tags(tmp_path) == set()

    def test_skips_unreadable_files(self, tmp_path):
        (tmp_path / "note.md").write_bytes(b"\xff\xfe invalid \x00\x01")
        tags = get_all_vault_tags(tmp_path)
        assert isinstance(tags, set)

    def test_aggregates_across_multiple_files(self, tmp_path):
        (tmp_path / "a.md").write_text("---\ntags:\n  - sql\n---\nA")
        (tmp_path / "b.md").write_text("---\ntags:\n  - duckdb\n---\nB")
        assert get_all_vault_tags(tmp_path) == {"sql", "duckdb"}

    def test_empty_string_tag_excluded(self, tmp_path):
        (tmp_path / "note.md").write_text("---\ntags: ''\n---\nContent")
        assert get_all_vault_tags(tmp_path) == set()

    def test_notes_without_category_still_contribute_tags(self, tmp_path):
        """Category is no longer required — notes without it must still yield tags."""
        (tmp_path / "note.md").write_text("---\ntags:\n  - no-category\n---\nContent")
        tags = get_all_vault_tags(tmp_path)
        assert "no-category" in tags
