"""Tests for the scan command in obsidian_vault_auto_tagger.logic."""
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from obsidian_vault_auto_tagger.logic import app
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
    def test_dry_run_prints_analysis(self, tmp_path, monkeypatch):
        vault = _make_vault(tmp_path)
        report = VaultTagReport(suggestions=[_suggestion()])

        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
        with patch("obsidian_vault_auto_tagger.logic.resolve_provider",
                   return_value=_mock_provider(report)):
            result = runner.invoke(app, ["--no-llm", "--dry-run"])

        assert result.exit_code == 0
        assert "Analysis complete" in result.output

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
        with patch("obsidian_vault_auto_tagger.logic.resolve_provider",
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
        with patch("obsidian_vault_auto_tagger.logic.resolve_provider",
                   return_value=_mock_provider(report)):
            result = runner.invoke(app, ["--limit", "2", "--no-llm"])
        assert result.exit_code == 0
