from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from fairguard_cli.client import APIClient, FairGuardAPIError
from fairguard_cli.config import FairGuardConfig, load_config, write_config

app = typer.Typer(
    name="fairguard",
    help="FairGuard AI Fairness Firewall — CLI",
    add_completion=False,
)
console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client(cfg: FairGuardConfig) -> APIClient:
    if not cfg.api_key:
        console.print(
            "[bold red]Error:[/] No API key found. Set FAIRGUARD_API_KEY or run [bold]fairguard init[/]."
        )
        raise typer.Exit(code=1)
    return APIClient(api_url=cfg.api_url, api_key=cfg.api_key)


def _verdict_badge(verdict: str) -> str:
    upper = verdict.upper()
    if upper == "PASS":
        return "[bold green]✔ PASS[/bold green]"
    if upper == "FAIL":
        return "[bold red]✘ FAIL[/bold red]"
    return f"[bold yellow]{upper}[/bold yellow]"


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

@app.command()
def init(
    api_url: str = typer.Option("https://api.fairguard.io", prompt="FairGuard API URL"),
    project_id: str = typer.Option(..., prompt="Project ID"),
    api_key: str = typer.Option(..., prompt="API Key", hide_input=True),
) -> None:
    """Initialize FairGuard project config and create .fairguard.yml."""
    cfg = FairGuardConfig(api_url=api_url, project_id=project_id, api_key=api_key)
    write_config(cfg)
    console.print(
        Panel(
            f"[green]Config saved to [bold].fairguard.yml[/bold][/green]\n"
            f"API URL   : {api_url}\n"
            f"Project ID: {project_id}\n"
            "[dim]API key is NOT written to disk — store it in FAIRGUARD_API_KEY.[/dim]",
            title="FairGuard Initialized",
            border_style="green",
        )
    )


# ---------------------------------------------------------------------------
# test
# ---------------------------------------------------------------------------

@app.command()
def test(
    data: Path = typer.Option(..., "--data", help="Path to CSV file with predictions"),
    project_id: Optional[str] = typer.Option(None, "--project-id", help="Project ID (overrides config)"),
    target: Optional[str] = typer.Option(None, "--target", help="Target / ground-truth column name"),
    prediction: Optional[str] = typer.Option(None, "--prediction", help="Prediction / score column name"),
    sensitive: Optional[str] = typer.Option(
        None, "--sensitive", help="Comma-separated sensitive attribute column names"
    ),
    endpoint_id: Optional[str] = typer.Option(None, "--endpoint-id", help="Endpoint ID for scoped audits"),
) -> None:
    """Run an offline fairness audit by uploading a CSV to the FairGuard API."""
    cfg = load_config()
    pid = project_id or cfg.project_id
    if not pid:
        console.print("[bold red]Error:[/] --project-id is required (or set in config).")
        raise typer.Exit(code=1)

    if not data.exists():
        console.print(f"[bold red]Error:[/] File not found: {data}")
        raise typer.Exit(code=1)

    extra: dict[str, str] = {"project_id": pid}
    if target:
        extra["target_column"] = target
    if prediction:
        extra["prediction_column"] = prediction
    if sensitive:
        extra["sensitive_columns"] = sensitive
    if endpoint_id:
        extra["endpoint_id"] = endpoint_id

    with console.status("[bold cyan]Running fairness audit…[/]"):
        with _get_client(cfg) as client:
            try:
                result = client.post_file("/api/v1/audit/offline", file_path=data, extra_fields=extra)
            except FairGuardAPIError as exc:
                console.print(f"[bold red]API Error {exc.status_code}:[/] {exc.detail}")
                raise typer.Exit(code=1)

    verdict = result.get("verdict", "UNKNOWN")
    audit_id = result.get("audit_id", "—")
    metrics: dict = result.get("metrics", {})

    console.print(
        Panel(
            f"Audit ID : [bold]{audit_id}[/bold]\nVerdict  : {_verdict_badge(verdict)}",
            title="FairGuard Audit Result",
            border_style="green" if verdict.upper() == "PASS" else "red",
        )
    )

    if metrics:
        table = Table(title="Fairness Metrics", show_lines=True)
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", justify="right")
        table.add_column("Threshold", justify="right")
        table.add_column("Status")
        for name, info in metrics.items():
            if isinstance(info, dict):
                val = f"{info.get('value', '—'):.4f}" if isinstance(info.get("value"), float) else str(info.get("value", "—"))
                threshold = str(info.get("threshold", "—"))
                status = _verdict_badge(info.get("status", "UNKNOWN"))
            else:
                val = str(info)
                threshold = "—"
                status = "—"
            table.add_row(name, val, threshold, status)
        console.print(table)

    violations: list = result.get("violations", [])
    if violations:
        console.print("\n[bold red]Violations:[/]")
        for v in violations:
            console.print(f"  [red]•[/red] {v}")

    raise typer.Exit(code=0 if verdict.upper() == "PASS" else 1)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

@app.command()
def report(
    project_id: Optional[str] = typer.Option(None, "--project-id", help="Project ID (overrides config)"),
    audit_id: Optional[str] = typer.Option(None, "--audit-id", help="Specific audit ID to report on"),
    output: Path = typer.Option(Path("fairguard-report.md"), "--output", help="Output markdown file path"),
) -> None:
    """Fetch audit results and generate a markdown report."""
    cfg = load_config()
    pid = project_id or cfg.project_id
    if not pid:
        console.print("[bold red]Error:[/] --project-id is required (or set in config).")
        raise typer.Exit(code=1)

    with console.status("[bold cyan]Fetching audit results…[/]"):
        with _get_client(cfg) as client:
            try:
                if audit_id:
                    result = client.get(f"/api/v1/audit/{audit_id}")
                else:
                    result = client.get(f"/api/v1/projects/{pid}/audits/latest")
            except FairGuardAPIError as exc:
                console.print(f"[bold red]API Error {exc.status_code}:[/] {exc.detail}")
                raise typer.Exit(code=1)

    verdict = result.get("verdict", "UNKNOWN")
    fetched_audit_id = result.get("audit_id", audit_id or "unknown")
    metrics: dict = result.get("metrics", {})
    violations: list = result.get("violations", [])
    created_at: str = result.get("created_at", "—")

    lines: list[str] = [
        "# FairGuard Audit Report",
        "",
        f"**Project ID:** `{pid}`  ",
        f"**Audit ID:** `{fetched_audit_id}`  ",
        f"**Created At:** {created_at}  ",
        f"**Verdict:** {'✔ PASS' if verdict.upper() == 'PASS' else '✘ FAIL'}",
        "",
        "## Fairness Metrics",
        "",
        "| Metric | Value | Threshold | Status |",
        "| ------ | ----: | --------: | ------ |",
    ]

    for name, info in metrics.items():
        if isinstance(info, dict):
            val = f"{info.get('value', '—'):.4f}" if isinstance(info.get("value"), float) else str(info.get("value", "—"))
            threshold = str(info.get("threshold", "—"))
            status = info.get("status", "UNKNOWN")
        else:
            val = str(info)
            threshold = "—"
            status = "UNKNOWN"
        lines.append(f"| {name} | {val} | {threshold} | {status} |")

    if violations:
        lines += ["", "## Violations", ""]
        for v in violations:
            lines.append(f"- {v}")

    lines += [
        "",
        "---",
        "_Generated by [FairGuard CLI](https://github.com/fairguard/fairguard)_",
    ]

    output.write_text("\n".join(lines))
    console.print(f"[green]Report saved to[/green] [bold]{output}[/bold]")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

@app.command()
def status(
    project_id: Optional[str] = typer.Option(None, "--project-id", help="Project ID (overrides config)"),
    endpoint_id: Optional[str] = typer.Option(None, "--endpoint-id", help="Specific endpoint ID"),
) -> None:
    """Show runtime monitoring status for a project or endpoint."""
    cfg = load_config()
    pid = project_id or cfg.project_id
    if not pid:
        console.print("[bold red]Error:[/] --project-id is required (or set in config).")
        raise typer.Exit(code=1)

    params: dict[str, str] = {}
    if endpoint_id:
        params["endpoint_id"] = endpoint_id

    with console.status("[bold cyan]Fetching runtime status…[/]"):
        with _get_client(cfg) as client:
            try:
                data = client.get(f"/api/v1/projects/{pid}/status", params=params)
            except FairGuardAPIError as exc:
                console.print(f"[bold red]API Error {exc.status_code}:[/] {exc.detail}")
                raise typer.Exit(code=1)

    overall = data.get("status", "UNKNOWN")
    endpoints: list = data.get("endpoints", [])

    console.print(
        Panel(
            f"Project : [bold]{pid}[/bold]\nStatus  : {_verdict_badge(overall)}",
            title="Runtime Monitoring Status",
            border_style="green" if overall.upper() in {"OK", "PASS", "HEALTHY"} else "yellow",
        )
    )

    if endpoints:
        table = Table(title="Endpoints", show_lines=True)
        table.add_column("Endpoint ID", style="cyan")
        table.add_column("Name")
        table.add_column("Requests (24h)", justify="right")
        table.add_column("Violations (24h)", justify="right")
        table.add_column("Status")
        for ep in endpoints:
            table.add_row(
                ep.get("endpoint_id", "—"),
                ep.get("name", "—"),
                str(ep.get("requests_24h", "—")),
                str(ep.get("violations_24h", "—")),
                _verdict_badge(ep.get("status", "UNKNOWN")),
            )
        console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
