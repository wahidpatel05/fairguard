"""Receipt management commands for the FairGuard CLI."""
from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.table import Table

from fairguard_cli.client import APIClient, FairGuardAPIError
from fairguard_cli.config import load_config

receipts_app = typer.Typer(help="Manage fairness audit receipts.")
console = Console()


@receipts_app.command("list")
def list_receipts(
    project_id: str = typer.Option(..., "--project-id", help="Project ID"),
) -> None:
    """List audit receipts for a project."""
    cfg = load_config()
    if not cfg.api_key:
        console.print("[bold red]Error:[/] Not configured. Run: fairguard init")
        raise typer.Exit(code=1)

    with APIClient(api_url=cfg.api_url, api_key=cfg.api_key) as client:
        try:
            receipts = client.get(
                "/api/v1/receipts/", params={"project_id": project_id}
            )
        except FairGuardAPIError as exc:
            console.print(f"[bold red]API Error {exc.status_code}:[/] {exc.detail}")
            raise typer.Exit(code=1)

    if not receipts:
        console.print("[yellow]No receipts found for this project.[/yellow]")
        return

    table = Table(title=f"Receipts — Project {project_id}", show_lines=True)
    table.add_column("Receipt ID", style="cyan", no_wrap=True)
    table.add_column("Verdict")
    table.add_column("Date")

    for r in receipts:
        verdict_raw = (r.get("verdict") or "unknown").lower()
        if verdict_raw == "pass":
            verdict_display = "[bold green]✔ PASS[/bold green]"
        elif verdict_raw == "fail":
            verdict_display = "[bold red]✘ FAIL[/bold red]"
        else:
            verdict_display = f"[bold yellow]{verdict_raw.upper()}[/bold yellow]"

        table.add_row(
            str(r.get("id", "—")),
            verdict_display,
            str(r.get("created_at", "—")),
        )

    console.print(table)


@receipts_app.command("verify")
def verify_receipt(
    receipt_id: str = typer.Option(..., "--receipt-id", help="Receipt ID to verify"),
) -> None:
    """Verify the cryptographic signature on a fairness receipt."""
    cfg = load_config()
    if not cfg.api_key:
        console.print("[bold red]Error:[/] Not configured. Run: fairguard init")
        raise typer.Exit(code=1)

    with APIClient(api_url=cfg.api_url, api_key=cfg.api_key) as client:
        try:
            result = client.post(f"/api/v1/receipts/{receipt_id}/verify")
        except FairGuardAPIError as exc:
            if exc.status_code == 404:
                console.print("[bold red]Receipt not found.[/bold red]")
            else:
                console.print(
                    f"[bold red]API Error {exc.status_code}:[/] {exc.detail}"
                )
            raise typer.Exit(code=1)

    if result.get("valid"):
        verified_at = result.get("verified_at", "—")
        console.print(
            f"[bold green]✓ Signature valid. Verified at {verified_at}[/bold green]"
        )
        raise typer.Exit(code=0)
    else:
        reason = result.get("reason", "Unknown reason")
        console.print(f"[bold red]✗ Invalid signature. Reason: {reason}[/bold red]")
        raise typer.Exit(code=1)
