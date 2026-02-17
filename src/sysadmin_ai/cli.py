"""Command-line interface for SysAdmin AI Next."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from sysadmin_ai import CostTracker, PlaybookGenerator, PolicyEngine, RecoveryEngine, SandboxManager
from sysadmin_ai.policy.engine import PolicyAction

console = Console()


@click.group()
@click.option("--config", "-c", type=click.Path(), help="Configuration file path")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, config: str | None, verbose: bool) -> None:
    """SysAdmin AI Next - Advanced AI-powered system administration."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config_path"] = config


@cli.command()
@click.option("--policy-dir", type=click.Path(), help="Policy directory")
@click.option("--opa-url", help="OPA server URL")
@click.option("--use-opa", is_flag=True, help="Use OPA for policy evaluation")
@click.argument("command")
@click.pass_context
def check(
    ctx: click.Context,
    policy_dir: str | None,
    opa_url: str | None,
    use_opa: bool,
    command: str,
) -> None:
    """Check if a command passes policy checks."""
    engine = PolicyEngine(
        policy_dir=policy_dir,
        opa_url=opa_url,
        use_opa=use_opa,
    )
    
    result = engine.evaluate(command)
    
    if result.allowed:
        console.print(f"[green]✓ ALLOWED[/green]: {result.message}")
    else:
        console.print(f"[red]✗ BLOCKED[/red]: {result.message}")
    
    if result.requires_confirmation:
        console.print("[yellow]⚠ REQUIRES CONFIRMATION[/yellow]")
    
    if ctx.obj.get("verbose"):
        console.print(f"\nAction: {result.action.value}")
        if result.rule:
            console.print(f"Rule: {result.rule.name} (severity: {result.rule.severity})")


@cli.command()
@click.option("--policy-dir", type=click.Path(), help="Policy directory")
@click.option("--opa-url", help="OPA server URL")
@click.option("--use-opa", is_flag=True, help="Use OPA for policy evaluation")
@click.argument("command")
@click.pass_context
def dry_run(
    ctx: click.Context,
    policy_dir: str | None,
    opa_url: str | None,
    use_opa: bool,
    command: str,
) -> None:
    """Show what would happen if a command were executed (dry-run mode)."""
    engine = PolicyEngine(
        policy_dir=policy_dir,
        opa_url=opa_url,
        use_opa=use_opa,
    )
    
    result = engine.dry_run(command)
    
    console.print(Panel.fit(f"Command: {command}"))
    
    # Create result table
    table = Table(title="Dry-Run Results")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Would Execute", "Yes" if result["would_execute"] else "No")
    table.add_row("Requires Confirmation", "Yes" if result["requires_confirmation"] else "No")
    table.add_row("Action", result["action"])
    table.add_row("Message", result["message"])
    
    if result["rule_matched"]:
        table.add_row("Rule Matched", result["rule_matched"])
    
    console.print(table)
    
    # Show matching rules
    if result["all_matching_rules"]:
        console.print("\n[yellow]All Matching Rules:[/yellow]")
        for rule in result["all_matching_rules"]:
            console.print(f"  - {rule['name']} ({rule['action']}, {rule['severity']})")


@cli.command()
@click.option("--backend", default="auto", help="Sandbox backend (docker, k8s, chroot, auto)")
@click.option("--user-id", help="User ID for sandbox isolation")
@click.option("--network", default="none", help="Network mode")
@click.option("--memory", default="512m", help="Memory limit")
@click.option("--cpu", default="1.0", help="CPU limit")
@click.argument("command")
def sandbox_run(
    backend: str,
    user_id: str | None,
    network: str,
    memory: str,
    cpu: str,
    command: str,
) -> None:
    """Run a command in an isolated sandbox."""
    manager = SandboxManager(backend=backend)
    
    from sysadmin_ai.sandbox.manager import SandboxConfig
    
    config = SandboxConfig(
        user_id=user_id,
        network_mode=network,
        memory_limit=memory,
        cpu_limit=cpu,
    )
    
    with console.status("[bold green]Creating sandbox..."):
        sandbox = manager.create_sandbox(user_id=user_id, config=config)
    
    console.print(f"[green]Created sandbox:[/green] {sandbox.id}")
    
    try:
        with console.status("[bold green]Executing command..."):
            result = manager.execute_in_sandbox(sandbox.id, command)
        
        if result["stdout"]:
            console.print(Panel(result["stdout"], title="Output", border_style="green"))
        
        if result["stderr"]:
            console.print(Panel(result["stderr"], title="Errors", border_style="red"))
        
        exit_code = result["exit_code"]
        if exit_code == 0:
            console.print(f"[green]Exit code: {exit_code}[/green]")
        else:
            console.print(f"[red]Exit code: {exit_code}[/red]")
    
    finally:
        manager.destroy_sandbox(sandbox.id)
        console.print("[dim]Sandbox destroyed[/dim]")


@cli.command()
@click.option("--format", "fmt", default="ansible", help="Output format (ansible, terraform, shell)")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--session-file", type=click.Path(exists=True), help="Session JSON file")
def generate_playbook(
    fmt: str,
    output: str | None,
    session_file: str | None,
) -> None:
    """Generate infrastructure-as-code from a session."""
    generator = PlaybookGenerator()
    
    # Create a sample session for demo
    from sysadmin_ai.playbooks.generator import Session, SessionCommand
    import time
    
    session = Session(
        session_id="demo-session",
        commands=[
            SessionCommand(
                command="apt install nginx",
                output="Reading package lists...",
                exit_code=0,
                timestamp=time.time(),
            ),
            SessionCommand(
                command="systemctl enable nginx",
                output="Created symlink...",
                exit_code=0,
                timestamp=time.time(),
            ),
            SessionCommand(
                command="systemctl start nginx",
                output="",
                exit_code=0,
                timestamp=time.time(),
            ),
        ],
    )
    
    if fmt == "ansible":
        result = generator.generate_ansible(session)
        content = result["yaml"]
        console.print("[green]Generated Ansible Playbook:[/green]")
    elif fmt == "terraform":
        result = generator.generate_terraform(session)
        content = result["hcl"]
        console.print("[green]Generated Terraform Config:[/green]")
    else:
        content = generator.generate_shell_script(session)
        console.print("[green]Generated Shell Script:[/green]")
    
    console.print(Panel(content, border_style="blue"))
    
    if output:
        Path(output).write_text(content)
        console.print(f"[green]Saved to:[/green] {output}")


@cli.command()
@click.argument("command")
def suggest(command: str) -> None:
    """Suggest safe alternatives for a blocked command."""
    recovery = RecoveryEngine()
    
    suggestions = recovery.suggest_alternatives(command)
    
    if not suggestions:
        console.print("[yellow]No suggestions available for this command.[/yellow]")
        return
    
    console.print(Panel.fit(f"Original: {command}"))
    
    for i, suggestion in enumerate(suggestions[:3], 1):
        style = "green" if suggestion.safe else "red"
        console.print(f"\n[bold]{i}. Alternative (confidence: {suggestion.confidence:.0%})[/bold]")
        console.print(f"  [{style}]{suggestion.suggestion}[/{style}]")
        console.print(f"  [dim]{suggestion.reason}[/dim]")


@cli.command()
@click.option("--date", help="Date for report (YYYY-MM-DD), default: today")
@click.option("--export", type=click.Path(), help="Export report to file")
@click.option("--format", "fmt", default="markdown", help="Export format (json, csv, markdown)")
def cost_report(date: str | None, export: str | None, fmt: str) -> None:
    """Show cost and usage report."""
    tracker = CostTracker()
    
    # Show daily report
    report = tracker.get_daily_report(date)
    
    console.print(Panel.fit(f"Cost Report for {report['date']}"))
    
    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Records", str(report["total_records"]))
    table.add_row("Total Cost", f"${report['total_cost_usd']:.4f}")
    table.add_row("Sessions", str(len(report["sessions"])))
    
    console.print(table)
    
    # Show session breakdown
    if report["sessions"]:
        console.print("\n[bold]Session Breakdown:[/bold]")
        session_table = Table()
        session_table.add_column("Session ID", style="cyan")
        session_table.add_column("Commands", style="green")
        session_table.add_column("Tokens", style="blue")
        session_table.add_column("Cost", style="yellow")
        
        for sid, stats in report["sessions"].items():
            tokens = stats["input_tokens"] + stats["output_tokens"]
            session_table.add_row(
                sid[:16] + "...",
                str(stats["commands"]),
                f"{tokens:,}",
                f"${stats['cost']:.4f}",
            )
        
        console.print(session_table)
    
    # Export if requested
    if export:
        tracker.export_report(export, fmt)
        console.print(f"[green]Exported to:[/green] {export}")


@cli.command()
def list_policies() -> None:
    """List all loaded security policies."""
    engine = PolicyEngine()
    rules = engine.list_rules()
    
    table = Table(title="Security Policies")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Action", style="green")
    table.add_column("Severity", style="yellow")
    
    for rule in rules:
        action_color = {
            "allow": "green",
            "block": "red",
            "confirm": "yellow",
            "log": "blue",
        }.get(rule.action.value, "white")
        
        table.add_row(
            rule.name,
            rule.description[:50] + "..." if len(rule.description) > 50 else rule.description,
            f"[{action_color}]{rule.action.value}[/{action_color}]",
            rule.severity,
        )
    
    console.print(table)


@cli.command()
@click.option("--host", default="127.0.0.1", help="Bind address")
@click.option("--port", default=8080, help="Port number")
@click.option("--policy-dir", type=click.Path(), help="Policy directory")
def serve(host: str, port: int, policy_dir: str | None) -> None:
    """Start the API server."""
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import JSONResponse
        import uvicorn
        
        app = FastAPI(title="SysAdmin AI Next API")
        engine = PolicyEngine(policy_dir=policy_dir)
        
        @app.get("/health")
        async def health() -> dict[str, str]:
            return {"status": "healthy"}
        
        @app.post("/check")
        async def check_command(request: dict) -> dict:
            command = request.get("command", "")
            if not command:
                raise HTTPException(status_code=400, detail="command is required")
            
            result = engine.evaluate(command)
            return {
                "allowed": result.allowed,
                "action": result.action.value,
                "message": result.message,
                "requires_confirmation": result.requires_confirmation,
            }
        
        @app.post("/dry-run")
        async def dry_run_endpoint(request: dict) -> dict:
            command = request.get("command", "")
            if not command:
                raise HTTPException(status_code=400, detail="command is required")
            
            return engine.dry_run(command)
        
        console.print(f"[green]Starting server on {host}:{port}[/green]")
        uvicorn.run(app, host=host, port=port)
    
    except ImportError:
        console.print("[red]FastAPI/uvicorn not installed. Install with: pip install fastapi uvicorn[/red]")
        sys.exit(1)


def main() -> None:
    """Entry point."""
    cli()


if __name__ == "__main__":
    main()
