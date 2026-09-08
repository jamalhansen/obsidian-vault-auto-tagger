import os
from pathlib import Path
from typing import Set

import frontmatter
from local_first_common.models import ContentMetadata


class VaultTaggerError(Exception):
    """Base typed error for obsidian-vault-auto-tagger."""


class ProviderSetupError(VaultTaggerError):
    """Raised when provider resolution fails."""


class LLMRunError(VaultTaggerError):
    """Raised when the LLM tagging call fails."""


def get_all_vault_tags(vault_path: Path) -> Set[str]:
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
                except Exception:
                    continue
    return all_tags
