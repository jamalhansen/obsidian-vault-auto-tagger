"""Tests for the scan command in obsidian_vault_auto_tagger.logic."""
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from obsidian_vault_auto_tagger.cli import app
from obsidian_vault_auto_tagger.schema import TagSuggestion, VaultTagReport

runner = CliRunner()


def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "note.md").write_text("---\ntags:\n  - ai\n---\n# Test\nContent here.")
    return vault


def _mock_provider(report: VaultTagReport):
    provider = MagicMock()
    provider.model = "mock"
    provider.complete = MagicMock(return_value=report)
    return provider


def _suggestion(file_path="note.md"):
    return TagSuggestion(
        file_path=file_path,
        existing_tags=["ai"],
        suggested_tags=["ai", "llm"],
        reasoning="Added llm tag.",
    )


class TestScanCommand:
    def test_suggestions_only_without_apply(self, tmp_path, monkeypatch):
        """Without --apply, nothing is ever written regardless of --dry-run --
        this is the "prototype" behavior scan() always had before --apply
        existed (see core.apply_tag_suggestion's docstring)."""
        vault = _make_vault(tmp_path)
        report = VaultTagReport(suggestions=[_suggestion()])

        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
        with patch("obsidian_vault_auto_tagger.cli.resolve_provider",
                   return_value=_mock_provider(report)):
            result = runner.invoke(app, ["--no-llm", "--dry-run"])

        assert result.exit_code == 0
        assert "Suggestions only" in result.output
        assert (vault / "note.md").read_text() == "---\ntags:\n  - ai\n---\n# Test\nContent here."

    def test_dry_run_with_apply_shows_what_would_change_without_writing(self, tmp_path, monkeypatch):
        # Not --no-llm: that flag always implies dry-run (resolve_dry_run's
        # own rule), which would make this test pass for the wrong reason.
        # The provider is mocked below, so no real LLM call happens either way.
        vault = _make_vault(tmp_path)
        report = VaultTagReport(suggestions=[_suggestion()])
        original = (vault / "note.md").read_text()

        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
        with patch("obsidian_vault_auto_tagger.cli.resolve_provider",
                   return_value=_mock_provider(report)):
            result = runner.invoke(app, ["--dry-run", "--apply"])

        assert result.exit_code == 0
        assert "[dry-run] Would apply" in result.output
        assert (vault / "note.md").read_text() == original

    def test_apply_writes_suggested_tags_into_the_file(self, tmp_path, monkeypatch):
        vault = _make_vault(tmp_path)
        report = VaultTagReport(suggestions=[_suggestion()])

        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
        with patch("obsidian_vault_auto_tagger.cli.resolve_provider",
                   return_value=_mock_provider(report)):
            result = runner.invoke(app, ["--apply"])

        assert result.exit_code == 0
        assert "Applied tags to 1/1 files" in result.output
        import frontmatter as fm
        post = fm.load(vault / "note.md")
        assert post.metadata["tags"] == ["ai", "llm"]

    def test_only_missing_tags_skips_files_that_already_have_tags(self, tmp_path, monkeypatch):
        vault = _make_vault(tmp_path)  # note.md already has tags: [ai]
        (vault / "untagged.md").write_text("---\ntitle: no tags yet\n---\nContent.")
        report = VaultTagReport(suggestions=[])
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))

        captured = {}

        def fake_complete(system, user, response_model=None):
            captured["user"] = user
            return report

        provider = MagicMock()
        provider.model = "mock"
        provider.complete = MagicMock(side_effect=fake_complete)
        with patch("obsidian_vault_auto_tagger.cli.resolve_provider", return_value=provider):
            result = runner.invoke(app, ["--no-llm", "--only-missing-tags"])

        assert result.exit_code == 0
        assert "untagged.md" in captured["user"]
        assert "note.md" not in captured["user"]

    def test_missing_vault_path_exits(self, monkeypatch):
        monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
        result = runner.invoke(app, ["--no-llm"])
        assert result.exit_code != 0

    def test_nonexistent_scan_path_exits(self, tmp_path, monkeypatch):
        vault = _make_vault(tmp_path)
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
        result = runner.invoke(app, ["--folder", str(tmp_path / "nonexistent"), "--no-llm"])
        assert result.exit_code != 0

    def test_no_markdown_files_found(self, tmp_path, monkeypatch):
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
        with patch("obsidian_vault_auto_tagger.cli.resolve_provider",
                   return_value=_mock_provider(VaultTagReport(suggestions=[]))):
            result = runner.invoke(app, ["--no-llm"])
        assert result.exit_code == 0
        assert "No markdown files" in result.output

    def test_limit_respected(self, tmp_path, monkeypatch):
        vault = _make_vault(tmp_path)
        for i in range(5):
            (vault / f"note{i}.md").write_text(f"---\ntags:\n  - t{i}\n---\nContent {i}")
        report = VaultTagReport(suggestions=[])
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
        with patch("obsidian_vault_auto_tagger.cli.resolve_provider",
                   return_value=_mock_provider(report)):
            result = runner.invoke(app, ["--limit", "2", "--no-llm"])
        assert result.exit_code == 0
