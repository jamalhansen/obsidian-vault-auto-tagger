import os
from pathlib import Path
from typing import Annotated

import frontmatter
import typer
from local_first_common.cli import (
    debug_option,
    dry_run_option,
    init_config_option,
    model_option,
    no_llm_option,
    provider_option,
    resolve_dry_run,
    resolve_provider,
    verbose_option,
)
from local_first_common.config import get_setting
from local_first_common.models import ContentMetadata
from local_first_common.providers import PROVIDERS
from local_first_common.tracking import register_tool, timed_run
from rich.console import Console
from rich.table import Table

from .core import LLMRunError, VaultTaggerError, get_all_vault_tags
from .prompts import build_system_prompt, build_user_prompt
from .schema import VaultTagReport

TOOL_NAME = "obsidian-vault-auto-tagger"

DEFAULTS = {"provider": "ollama", "model": "llama3.2:3b"}
_TOOL = register_tool(TOOL_NAME)

console = Console()
app = typer.Typer(help="Scans vault files and suggests consistent tags using LLM.")


def display_suggestions(report: VaultTagReport):
    """Rich display of tag suggestions."""
    if not report.suggestions:
        console.print("[yellow]No suggestions generated.[/yellow]")
        return

    table = Table(title="Tag Suggestions")
    table.add_column("File", style="cyan")
    table.add_column("Current Tags", style="dim")
    table.add_column("Suggested Tags", style="green bold")
    table.add_column("Reasoning", style="italic")

    for s in report.suggestions:
        table.add_row(
            os.path.basename(s.file_path),
            ", ".join(s.existing_tags),
            ", ".join(s.suggested_tags),
            s.reasoning,
        )
    console.print(table)


@app.command()
def scan(
    folder: Annotated[
        Path | None, typer.Option("--folder", "-f", help="Specific folder to scan in vault.")
    ] = None,
    limit: Annotated[
        int, typer.Option("--limit", "-l", help="Limit number of files to process.")
    ] = 10,
    provider: Annotated[str, provider_option(PROVIDERS)] = os.environ.get(
        "MODEL_PROVIDER", "ollama"
    ),
    model: Annotated[str | None, model_option()] = None,
    dry_run: Annotated[bool, dry_run_option()] = False,
    no_llm: Annotated[bool, no_llm_option()] = False,
    verbose: Annotated[bool, verbose_option()] = False,
    debug: Annotated[bool, debug_option()] = False,
    init_config: Annotated[bool, init_config_option(TOOL_NAME, DEFAULTS)] = False,
):
    """Scan vault and suggest tags."""
    dry_run = resolve_dry_run(dry_run, no_llm)

    vault_path_str = os.getenv("OBSIDIAN_VAULT_PATH")
    if not vault_path_str:
        console.print(
            "[red]Error: OBSIDIAN_VAULT_PATH environment variable not set.[/red]"
        )
        raise typer.Exit(1)

    vault_path = Path(vault_path_str)
    scan_path = (
        folder if folder and folder.is_absolute() else (vault_path / (folder or "."))
    )

    if not scan_path.exists():
        console.print(f"[red]Error: Scan path {scan_path} does not exist.[/red]")
        raise typer.Exit(1)

    # 1. Gather all tags in vault for context
    if verbose:
        console.print("Scanning vault for existing tags...")
    all_existing_tags = sorted(get_all_vault_tags(vault_path))

    # 2. Collect files to process
    files_to_process = []
    for root, _, files in os.walk(scan_path):
        for file in files:
            if file.endswith(".md"):
                file_path = Path(root) / file
                files_to_process.append(file_path)
                if len(files_to_process) >= limit:
                    break
        if len(files_to_process) >= limit:
            break

    if not files_to_process:
        console.print("[yellow]No markdown files found to process.[/yellow]")
        return

    # 3. Read content
    notes_data = []
    for f in files_to_process:
        try:
            post = frontmatter.load(f)
            meta = ContentMetadata.from_metadata(post.metadata)
            notes_data.append(
                {
                    "path": str(f.relative_to(vault_path)),
                    "content": post.content[
                        :2000
                    ],  # Truncate content for prompt efficiency
                    "tags": meta.tags,
                    "category": meta.category_name,
                }
            )
        except Exception as e:  # noqa: BLE001 - a malformed note should be skipped, not crash the scan
            if verbose:
                console.print(f"[yellow]Skipping {f}: {e}[/yellow]")

    # 4. LLM processing
    try:
        actual_provider = get_setting(
            TOOL_NAME, "provider", cli_val=provider, default="ollama"
        )
        actual_model = get_setting(
            TOOL_NAME, "model", cli_val=model, default=DEFAULTS["model"]
        )
        llm = resolve_provider(
            PROVIDERS, actual_provider, actual_model, debug=debug, no_llm=no_llm
        )
    except VaultTaggerError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:  # noqa: BLE001 - top-level CLI boundary: report cleanly and exit
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    system = build_system_prompt(all_existing_tags)
    user = build_user_prompt(notes_data)

    try:
        with timed_run(
            "obsidian-vault-auto-tagger", llm.model, source_location=str(scan_path)
        ) as run:
            response = llm.complete(system, user, response_model=VaultTagReport)
            result = response
            run.item_count = len(notes_data)
    except LLMRunError as e:
        console.print(f"[red]Error during LLM processing: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:  # noqa: BLE001 - top-level CLI boundary: report cleanly and exit
        console.print(f"[red]Error during LLM processing: {e}[/red]")
        raise typer.Exit(1)

    display_suggestions(result)

    if dry_run:
        console.print(
            "\n[yellow][dry-run] Analysis complete. No tags applied.[/yellow]"
        )
    else:
        console.print(
            "\n[bold]Note:[/bold] Tag application is manual or via a separate 'apply' command (not implemented in this prototype)."
        )


if __name__ == "__main__":
    app()
