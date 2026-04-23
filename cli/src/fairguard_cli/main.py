"""FairGuard CLI — main entry point."""
from __future__ import annotations

import pathlib
import sys
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from fairguard_cli.client import APIClient, FairGuardAPIError
from fairguard_cli.commands.receipts import receipts_app
from fairguard_cli.config import (
    FairGuardConfig,
    load_config,
    save_global_config,
    write_config,
)

app = typer.Typer(
    name="fairguard",
    help="FairGuard CLI — AI Fairness Audit Platform",
    add_completion=False,
)
app.add_typer(receipts_app, name="receipts")

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_client(cfg: FairGuardConfig) -> APIClient:
    if not cfg.api_key:
        console.print(
            "[bold red]Error:[/] Not configured. Run: [bold]fairguard init[/]"
        )
        raise typer.Exit(code=1)
    return APIClient(api_url=cfg.api_url, api_key=cfg.api_key)


def _verdict_style(verdict: str) -> str:
    v = verdict.lower()
    if v == "pass":
        return "[bold green]✔ PASS[/bold green]"
    if v == "fail":
        return "[bold red]✘ FAIL[/bold red]"
    if v == "pass_with_warnings":
        return "[bold yellow]⚠ PASS WITH WARNINGS[/bold yellow]"
    return f"[bold]{verdict.upper()}[/]"


def _status_style(status: str) -> str:
    s = status.lower()
    if s in ("healthy", "pass"):
        return "[bold green]✔ HEALTHY[/bold green]"
    if s == "warning":
        return "[bold yellow]⚠ WARNING[/bold yellow]"
    if s == "critical":
        return "[bold red]✘ CRITICAL[/bold red]"
    return f"[dim]{status}[/dim]"


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@app.command()
def init(
    api_url: Optional[str] = typer.Option(None, "--api-url", help="FairGuard API base URL"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key", hide_input=True),
    no_interactive: bool = typer.Option(False, "--no-interactive", help="Skip prompts (for CI)"),
) -> None:
    """Initialize FairGuard credentials and test the connection."""
    if not no_interactive:
        if api_url is None:
            api_url = typer.prompt("FairGuard API URL", default="http://localhost:8000/api/v1")
        if api_key is None:
            api_key = typer.prompt("API Key", hide_input=True)
    else:
        if api_url is None or api_key is None:
            console.print(
                "[bold red]Error:[/] --api-url and --api-key are required with --no-interactive"
            )
            raise typer.Exit(code=1)

    # Normalise URL — strip trailing slash
    api_url = api_url.rstrip("/")

    # Test connection via GET /auth/me
    console.print("[cyan]Testing connection…[/cyan]")
    try:
        response = httpx.get(
            f"{api_url}/auth/me",
            headers={"X-API-Key": api_key},
            timeout=15.0,
        )
    except httpx.ConnectError as exc:
        console.print(f"[bold red]Connection failed:[/] {exc}")
        raise typer.Exit(code=1)
    except httpx.TimeoutException:
        console.print("[bold red]Connection timed out.[/bold red]")
        raise typer.Exit(code=1)

    if response.status_code == 200:
        user = response.json()
        full_name = user.get("full_name") or user.get("email", "unknown")
        save_global_config(api_url, api_key)
        console.print(
            Panel(
                f"[green]✓ Connected as [bold]{full_name}[/bold][/green]\n"
                f"API URL: {api_url}\n"
                "[dim]Credentials saved to ~/.fairguard/config.json[/dim]",
                title="FairGuard Initialized",
                border_style="green",
            )
        )
    else:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        console.print(
            f"[bold red]Authentication failed (HTTP {response.status_code}):[/] {detail}"
        )
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# test
# ---------------------------------------------------------------------------


@app.command()
def test(
    data: pathlib.Path = typer.Option(..., "--data", help="CSV file path"),
    project_id: str = typer.Option(..., "--project-id", help="Project ID"),
    target: str = typer.Option(..., "--target", help="Target/ground-truth column name"),
    prediction: str = typer.Option(..., "--prediction", help="Prediction column name"),
    sensitive: str = typer.Option(
        ..., "--sensitive", help="Comma-separated sensitive attribute column names"
    ),
) -> None:
    """Run an offline fairness audit by uploading a CSV to FairGuard."""
    # Validate file
    if not data.exists():
        console.print(f"[bold red]Error:[/] File not found: {data}")
        raise typer.Exit(code=1)
    if data.suffix.lower() != ".csv":
        console.print(f"[bold red]Error:[/] File must be a CSV: {data}")
        raise typer.Exit(code=1)

    cfg = load_config()

    with console.status("[bold cyan]Running fairness audit…[/]"):
        with _get_client(cfg) as client:
            try:
                result = client.post_file(
                    "/api/v1/audit/offline",
                    file_path=data,
                    extra_fields={
                        "project_id": project_id,
                        "target_column": target,
                        "prediction_column": prediction,
                        "sensitive_columns": sensitive,
                    },
                )
            except FairGuardAPIError as exc:
                console.print(f"[bold red]API Error {exc.status_code}:[/] {exc.detail}")
                raise typer.Exit(code=1)

    audit = result.get("audit", {})
    verdict = (audit.get("verdict") or "unknown").lower()
    audit_id = audit.get("id", "—")
    contract_evaluations: list = result.get("contract_evaluations", [])
    recommendations: list = result.get("recommendations", [])
    receipt_id = result.get("receipt_id")

    # Contract evaluation table
    if contract_evaluations:
        table = Table(title="Contract Evaluations", show_lines=True)
        table.add_column("Contract", style="cyan", no_wrap=True)
        table.add_column("Attribute")
        table.add_column("Metric")
        table.add_column("Value", justify="right")
        table.add_column("Threshold", justify="right")
        table.add_column("Status")

        for ev in contract_evaluations:
            passed = ev.get("passed", True)
            severity = (ev.get("severity") or "").lower()

            if passed:
                status_cell = "[bold green]✔ PASS[/bold green]"
            elif severity == "warn":
                status_cell = "[bold yellow]⚠ WARN[/bold yellow]"
            else:
                status_cell = "[bold red]✘ FAIL[/bold red]"

            value = ev.get("value")
            val_str = f"{value:.4f}" if isinstance(value, float) else str(value or "—")
            threshold = ev.get("threshold")
            thr_str = f"{threshold:.4f}" if isinstance(threshold, float) else str(threshold or "—")

            table.add_row(
                str(ev.get("contract_id", "—")),
                str(ev.get("attribute") or "—"),
                str(ev.get("metric", "—")),
                val_str,
                thr_str,
                status_cell,
            )

        console.print(table)

    # Overall verdict
    border = "green" if verdict == "pass" else ("yellow" if verdict == "pass_with_warnings" else "red")
    details = f"Audit ID : [bold]{audit_id}[/bold]\nVerdict  : {_verdict_style(verdict)}"
    if receipt_id:
        details += f"\nReceipt  : [bold]{receipt_id}[/bold]"
    console.print(Panel(details, title="FairGuard Audit Result", border_style=border))

    # Recommendations
    if recommendations:
        console.print(f"\n[bold yellow]Recommendations ({len(recommendations)}):[/]")
        for rec in recommendations:
            if isinstance(rec, dict):
                msg = rec.get("recommendation") or rec.get("message") or str(rec)
            else:
                msg = str(rec)
            console.print(f"  [yellow]•[/yellow] {msg}")

    # Exit codes: pass=0, pass_with_warnings=1, fail=2
    if verdict == "pass":
        raise typer.Exit(code=0)
    elif verdict == "pass_with_warnings":
        raise typer.Exit(code=1)
    else:
        raise typer.Exit(code=2)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


@app.command()
def report(
    audit_id: str = typer.Option(..., "--audit-id", help="Audit ID to generate report for"),
    format: str = typer.Option("pdf", "--format", help="Output format: pdf or markdown"),
    output: Optional[pathlib.Path] = typer.Option(
        None, "--output", help="Output file path (default: audit_{id}.{format})"
    ),
) -> None:
    """Download an audit report (PDF or Markdown) from FairGuard."""
    if format not in ("pdf", "markdown"):
        console.print("[bold red]Error:[/] --format must be 'pdf' or 'markdown'")
        raise typer.Exit(code=1)

    if output is None:
        ext = "pdf" if format == "pdf" else "md"
        output = pathlib.Path(f"audit_{audit_id}.{ext}")

    cfg = load_config()

    with console.status(f"[bold cyan]Downloading {format} report…[/]"):
        with _get_client(cfg) as client:
            try:
                content = client.get_bytes(f"/api/v1/reports/{audit_id}/{format}")
            except FairGuardAPIError as exc:
                if exc.status_code == 404:
                    console.print("[bold red]Audit not found.[/bold red]")
                else:
                    console.print(
                        f"[bold red]API Error {exc.status_code}:[/] {exc.detail}"
                    )
                raise typer.Exit(code=1)

    output.write_bytes(content)
    console.print(f"[bold green]✓ Report saved to {output}[/bold green]")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@app.command()
def status(
    project_id: str = typer.Option(..., "--project-id", help="Project ID"),
    aggregation_key: Optional[str] = typer.Option(
        None, "--aggregation-key", help="Optional aggregation key"
    ),
) -> None:
    """Show runtime monitoring status for a project."""
    cfg = load_config()

    params: dict = {"project_id": project_id}
    if aggregation_key:
        params["aggregation_key"] = aggregation_key

    with console.status("[bold cyan]Fetching runtime status…[/]"):
        with _get_client(cfg) as client:
            try:
                data = client.get("/api/v1/runtime/status", params=params)
            except FairGuardAPIError as exc:
                console.print(f"[bold red]API Error {exc.status_code}:[/] {exc.detail}")
                raise typer.Exit(code=1)

    overall = data.get("overall_status", "no_data")
    windows: dict = data.get("windows", {})

    # Windows summary table
    if windows:
        win_table = Table(title="Runtime Windows", show_lines=True)
        win_table.add_column("Window", style="cyan", no_wrap=True)
        win_table.add_column("Count", justify="right")
        win_table.add_column("Status")
        win_table.add_column("Evaluated At")

        for window_name, wdata in windows.items():
            win_table.add_row(
                window_name,
                str(wdata.get("count", 0)),
                _status_style(wdata.get("status", "—")),
                str(wdata.get("evaluated_at") or "—"),
            )
        console.print(win_table)

        # Per-window contract evaluations (if any)
        for window_name, wdata in windows.items():
            metrics = wdata.get("metrics", {})
            contract_evals = metrics.get("contract_evaluation", [])
            if contract_evals:
                eval_table = Table(
                    title=f"Contract Evaluations — {window_name} window",
                    show_lines=True,
                )
                eval_table.add_column("Contract", style="cyan", no_wrap=True)
                eval_table.add_column("Attribute")
                eval_table.add_column("Metric")
                eval_table.add_column("Value", justify="right")
                eval_table.add_column("Threshold", justify="right")
                eval_table.add_column("Status")
                for ev in contract_evals:
                    passed = ev.get("passed", True)
                    severity = (ev.get("severity") or "").lower()
                    if passed:
                        st = "[bold green]✔ PASS[/bold green]"
                    elif severity == "warn":
                        st = "[bold yellow]⚠ WARN[/bold yellow]"
                    else:
                        st = "[bold red]✘ FAIL[/bold red]"
                    value = ev.get("value")
                    val_str = f"{value:.4f}" if isinstance(value, float) else str(value or "—")
                    threshold = ev.get("threshold")
                    thr_str = f"{threshold:.4f}" if isinstance(threshold, float) else str(threshold or "—")
                    eval_table.add_row(
                        str(ev.get("contract_id", "—")),
                        str(ev.get("attribute") or "—"),
                        str(ev.get("metric", "—")),
                        val_str,
                        thr_str,
                        st,
                    )
                console.print(eval_table)

    # Overall status panel
    border = "green" if overall in ("healthy", "pass") else ("yellow" if overall == "warning" else "red")
    console.print(
        Panel(
            f"Project : [bold]{project_id}[/bold]\nStatus  : {_status_style(overall)}",
            title="Overall Runtime Status",
            border_style=border,
        )
    )

    # Exit codes: healthy/no_data=0, warning=1, critical=2
    if overall in ("healthy", "no_data", "pass"):
        raise typer.Exit(code=0)
    elif overall == "warning":
        raise typer.Exit(code=1)
    else:
        raise typer.Exit(code=2)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
