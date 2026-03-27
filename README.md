# Obsidian Vault Auto-Tagger

Scans vault files, extracts key concepts, and suggests consistent tags using an LLM.

## Features
- **Context-Aware**: Pulls existing tags from the vault to prioritize consistency.
- **Kebab-Case Enforcement**: Ensures new tags follow a standard format.
- **Reasoning**: Provides an explanation for why specific tags were suggested.
- **Limit & Filter**: Process specific folders or a subset of files.

## Installation
```bash
uv sync
```

## Usage
```bash
export OBSIDIAN_VAULT_PATH="/path/to/your/vault"
uv run vault-auto-tagger scan -f "projects/ai" -l 20
```

Standard flags supported: `--dry-run`, `--no-llm`, `--provider`, `--model`.
