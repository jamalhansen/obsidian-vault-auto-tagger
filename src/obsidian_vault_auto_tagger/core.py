import os
from pathlib import Path

import frontmatter
from local_first_common.models import ContentMetadata


class VaultTaggerError(Exception):
    """Base typed error for obsidian-vault-auto-tagger."""


class ProviderSetupError(VaultTaggerError):
    """Raised when provider resolution fails."""


class LLMRunError(VaultTaggerError):
    """Raised when the LLM tagging call fails."""


def get_all_vault_tags(vault_path: Path) -> set[str]:
    """Scans the entire vault for existing tags in frontmatter."""
    all_tags = set()
    for root, _, files in os.walk(vault_path):
        for file in files:
            if file.endswith(".md"):
                file_path = Path(root) / file
                try:
                    post = frontmatter.load(file_path)
                    meta = ContentMetadata.from_metadata(post.metadata)
                    all_tags.update(meta.tags)
                except Exception:  # noqa: BLE001, S112 - a malformed note should be skipped, not crash the vault-wide scan
                    continue
    return all_tags


def apply_tag_suggestion(vault_path: Path, file_path: str, suggested_tags: list[str]) -> bool:
    """Write suggested_tags into one file's tags: field, merged with whatever
    tags it already had (union, not overwrite -- a suggestion adds to a
    file's tags, it doesn't get to discard ones already there). Returns
    False (does not raise) if the file can't be read/parsed -- an apply
    pass processing many files shouldn't die on one malformed note.

    This is the piece the tool's own docstring flagged as
    "not implemented in this prototype" until now -- scan() only ever
    suggested tags, nothing wrote them back.
    """
    full_path = vault_path / file_path
    try:
        post = frontmatter.load(full_path)
    except Exception:  # noqa: BLE001 - a malformed note should be skipped, not crash an apply pass over many files
        return False

    existing = post.metadata.get("tags") or []
    if isinstance(existing, str):
        existing = [t.strip() for t in existing.split(",") if t.strip()]

    merged = list(dict.fromkeys([*existing, *suggested_tags]))  # union, order-preserving, de-duplicated
    post.metadata["tags"] = merged
    full_path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return True
