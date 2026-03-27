import os
from pathlib import Path
from typing import Optional, Set

import typer
import frontmatter
from rich.console import Console
from rich.table import Table

from local_first_common.providers import PROVIDERS
from local_first_common.cli import (
    provider_option,
    model_option,
    dry_run_option,
    no_llm_option,
    verbose_option,
    debug_option,
    resolve_provider,
    resolve_dry_run,
)
from local_first_common.tracking import register_tool, timed_run

from .schema import VaultTagReport
from .prompts import build_system_prompt, build_user_prompt

_TOOL = register_tool("obsidian-vault-auto-tagger")
console = Console()
app = typer.Typer(help="Scans vault files and suggests consistent tags using LLM.")

def get_all_vault_tags(vault_path: Path) -> Set[str]:
    """Scans the entire vault for existing tags in frontmatter."""
    all_tags = set()
    for root, _, files in os.walk(vault_path):
        for file in files:
            if file.endswith(".md"):
                file_path = Path(root) / file
                try:
                    post = frontmatter.load(file_path)
                    tags = post.get("tags", [])
                    if isinstance(tags, str):
                        all_tags.add(tags)
                    elif isinstance(tags, list):
                        all_tags.update(tags)
                except Exception:
                    continue
    return all_tags

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
            s.reasoning
        )
    console.print(table)

@app.command()
def scan(
    folder: Optional[Path] = typer.Option(None, "--folder", "-f", help="Specific folder to scan in vault."),
    limit: int = typer.Option(10, "--limit", "-l", help="Limit number of files to process."),
    provider: str = provider_option(PROVIDERS),
    model: Optional[str] = model_option(),
    dry_run: bool = dry_run_option(),
    no_llm: bool = no_llm_option(),
    verbose: bool = verbose_option(),
    debug: bool = debug_option(),
):
    """Scan vault and suggest tags."""
    dry_run = resolve_dry_run(dry_run, no_llm)

    vault_path_str = os.getenv("OBSIDIAN_VAULT_PATH")
    if not vault_path_str:
        console.print("[red]Error: OBSIDIAN_VAULT_PATH environment variable not set.[/red]")
        raise typer.Exit(1)
    
    vault_path = Path(vault_path_str)
    scan_path = folder if folder and folder.is_absolute() else (vault_path / (folder or "."))
    
    if not scan_path.exists():
        console.print(f"[red]Error: Scan path {scan_path} does not exist.[/red]")
        raise typer.Exit(1)

    # 1. Gather all tags in vault for context
    if verbose:
        console.print("Scanning vault for existing tags...")
    all_existing_tags = sorted(list(get_all_vault_tags(vault_path)))

    # 2. Collect files to process
    files_to_process = []
    for root, _, files in os.walk(scan_path):
        for file in files:
            if file.endswith(".md"):
                file_path = Path(root) / file
                # Skip files that already have many tags? Or just process them.
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
            notes_data.append({
                "path": str(f.relative_to(vault_path)),
                "content": post.content[:2000], # Truncate content for prompt efficiency
                "tags": post.get("tags", [])
            })
        except Exception as e:
            if verbose:
                console.print(f"[yellow]Skipping {f}: {e}[/yellow]")

    # 4. LLM processing
    try:
        llm = resolve_provider(PROVIDERS, provider, model, debug=debug, no_llm=no_llm)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    system = build_system_prompt(all_existing_tags)
    user = build_user_prompt(notes_data)

    try:
        with timed_run("obsidian-vault-auto-tagger", llm.model, source_location=str(scan_path)) as run:
            response = llm.complete(system, user, response_model=VaultTagReport)
            result = response
            run.item_count = len(notes_data)
    except Exception as e:
        console.print(f"[red]Error during LLM processing: {e}[/red]")
        raise typer.Exit(1)

    display_suggestions(result)

    if dry_run:
        console.print("\n[yellow][dry-run] Analysis complete. No tags applied.[/yellow]")
    else:
        # Implement tag application logic if desired, or keep as suggestion-first
        console.print("\n[bold]Note:[/bold] Tag application is manual or via a separate 'apply' command (not implemented in this prototype).")

if __name__ == "__main__":
    app()
