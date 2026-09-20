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

# Preview suggestions only -- nothing is written without --apply
uv run vault-auto-tagger scan -f "projects/ai" -l 20

# Back-fill tags for files that don't have any yet, writing for real
uv run vault-auto-tagger scan -f "projects/ai" --only-missing-tags --apply
```

- `--apply` writes suggested tags into each file's `tags:` field, merged with any existing tags -- without it, suggestions are only printed.
- `--only-missing-tags` skips files that already have a non-empty tags field.
- Standard flags supported: `--dry-run`, `--no-llm`, `--provider`, `--model`.
