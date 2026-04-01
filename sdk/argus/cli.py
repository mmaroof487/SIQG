"""Argus CLI - Command-line interface for the Argus gateway.

Usage:
    argus login http://localhost:8000 admin password
    argus query "SELECT * FROM users LIMIT 10"
    argus explain "SELECT COUNT(*) FROM orders"
    argus nl-to-sql "How many users signed up in the last 7 days?"
    argus status
"""
import typer
import json
from pathlib import Path
from .client import Gateway
from typing import Optional

app = typer.Typer(
    name="argus",
    help="CLI for Argus - Secure Intelligent Query Gateway",
    no_args_is_help=True,
)

TOKEN_FILE = Path.home() / ".argus_token"


def _load_gateway() -> Gateway:
    """Load gateway from cached token file."""
    if not TOKEN_FILE.exists():
        typer.echo(
            "❌ Not logged in. Run: argus login <url> <username> <password>",
            err=True,
        )
        raise typer.Exit(1)

    try:
        content = TOKEN_FILE.read_text().strip()
        parts = content.split("\n")
        if len(parts) < 2:
            typer.echo("❌ Invalid token file format", err=True)
            raise typer.Exit(1)
        url, token = parts[0], parts[1]
        return Gateway(url, jwt_token=token)
    except Exception as e:
        typer.echo(f"❌ Failed to load gateway: {e}", err=True)
        raise typer.Exit(1)


def _save_gateway(url: str, token: str):
    """Save gateway URL and token to file."""
    TOKEN_FILE.write_text(f"{url}\n{token}")
    TOKEN_FILE.chmod(0o600)  # Restrict to owner only
    typer.echo(f"✅ Token saved to {TOKEN_FILE}")


@app.command()
def login(
    url: str = typer.Argument(..., help="Gateway URL (e.g., http://localhost:8000)"),
    username: str = typer.Argument(..., help="Username"),
    password: str = typer.Argument(..., help="Password"),
):
    """Log in to the Argus gateway and save credentials.

    Example:
        argus login http://localhost:8000 admin password
    """
    try:
        typer.echo(f"🔐 Logging in to {url}...")
        gw = Gateway(url)
        gw.login(username, password)

        # Extract token from header
        token = gw._headers.get("Authorization", "").split(" ")[-1]
        if not token or token == "":
            typer.echo("❌ Failed to get token", err=True)
            raise typer.Exit(1)

        _save_gateway(url, token)
        typer.echo(f"✅ Successfully logged in as {username}")
    except Exception as e:
        typer.echo(f"❌ Login failed: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def query(
    sql: str = typer.Argument(..., help="SQL query to execute"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Validate and estimate cost without executing"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output as JSON for scripting"
    ),
):
    """Execute a SQL query through Argus.

    Example:
        argus query "SELECT * FROM users LIMIT 10"
        argus query "SELECT * FROM users" --dry-run
    """
    try:
        gw = _load_gateway()

        typer.echo(f"🔍 Executing query...") if not json_output else None
        result = gw.query(sql, dry_run=dry_run)

        if json_output:
            typer.echo(json.dumps(result, indent=2))
        else:
            # Pretty print
            typer.echo(f"✅ Query executed")
            typer.echo(f"  Rows: {result.get('rows_count', 0)}")
            typer.echo(f"  Latency: {result.get('latency_ms', 0):.1f}ms")
            typer.echo(f"  Cached: {result.get('cached', False)}")
            typer.echo(f"  Cost: {result.get('cost', 0):.2f}")

            if dry_run:
                analysis = result.get("analysis", {})
                typer.echo(f"\n  Mode: {analysis.get('mode', 'unknown')}")
                checks = analysis.get("pipeline_checks", {})
                for check, status in checks.items():
                    typer.echo(f"    {check}: {status}")

            if result.get("rows"):
                typer.echo(f"\n  First row: {result['rows'][0]}")
    except Exception as e:
        typer.echo(f"❌ Query failed: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def explain(
    sql: str = typer.Argument(..., help="SQL query to explain"),
):
    """Explain what a SQL query does in plain English.

    Example:
        argus explain "SELECT COUNT(*) FROM orders WHERE status = 'pending'"
    """
    try:
        gw = _load_gateway()

        typer.echo(f"💡 Generating explanation...")
        explanation = gw.explain(sql)

        typer.echo(f"\n📝 Explanation:")
        typer.echo(f"  {explanation}")
    except Exception as e:
        typer.echo(f"❌ Explanation failed: {e}", err=True)
        raise typer.Exit(1)


@app.command(name="nl-to-sql")
def nl_to_sql(
    question: str = typer.Argument(..., help="Natural language question"),
    schema_hint: str = typer.Option(
        "", "--schema", help="Optional schema hint (e.g., 'table users(id, name)'"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output as JSON for scripting"
    ),
):
    """Convert natural language question to SQL and execute.

    Example:
        argus nl-to-sql "How many users signed up in the last 7 days?"
    """
    try:
        gw = _load_gateway()

        typer.echo(f"🤖 Converting question to SQL...") if not json_output else None
        result = gw.nl_to_sql(question, schema_hint=schema_hint)

        if json_output:
            typer.echo(json.dumps(result, indent=2))
        else:
            if result.get("status") == "error":
                typer.echo(f"❌ Error: {result.get('message', 'Unknown error')}", err=True)
                raise typer.Exit(1)

            typer.echo(f"✅ Question processed")
            typer.echo(f"\n  Generated SQL:")
            typer.echo(f"    {result.get('generated_sql', 'N/A')}")

            query_result = result.get("result", {})
            if query_result:
                typer.echo(f"\n  Results:")
                typer.echo(f"    Rows: {query_result.get('rows_count', 0)}")
                typer.echo(f"    Latency: {query_result.get('latency_ms', 0):.1f}ms")
                typer.echo(f"    Cost: {query_result.get('cost', 0):.2f}")

                if query_result.get("rows"):
                    typer.echo(f"\n  First row: {query_result['rows'][0]}")
    except Exception as e:
        typer.echo(f"❌ Failed: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def status(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Check Argus gateway status and health.

    Example:
        argus status
    """
    try:
        gw = _load_gateway()

        typer.echo(f"🏥 Checking status...") if not json_output else None
        result = gw.status()

        if json_output:
            typer.echo(json.dumps(result, indent=2))
        else:
            status_value = result.get("status", "unknown")
            db_status = result.get("db", "unknown")
            redis_status = result.get("redis", "unknown")

            # Emoji status indicators
            status_icon = "✅" if status_value == "ok" else "⚠️"
            db_icon = "✅" if db_status == "healthy" else "❌"
            redis_icon = "✅" if redis_status == "healthy" else "❌"

            typer.echo(f"\n{status_icon} Gateway Status: {status_value}")
            typer.echo(f"{db_icon} Database: {result.get('db', 'unknown')}")
            typer.echo(f"{redis_icon} Redis: {result.get('redis', 'unknown')}")

            # Also try to get metrics
            try:
                metrics = gw.metrics()
                typer.echo(f"\n📊 Metrics:")
                typer.echo(f"  Total requests: {metrics.get('requests_total', 0)}")
                typer.echo(f"  Cache hits: {metrics.get('cache_hits', 0)}")
                typer.echo(f"  Cache misses: {metrics.get('cache_misses', 0)}")
            except Exception:
                pass  # Metrics endpoint may not be available

    except Exception as e:
        typer.echo(f"❌ Status check failed: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def logout():
    """Clear saved credentials.

    Example:
        argus logout
    """
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        typer.echo("✅ Logged out - token cleared")
    else:
        typer.echo("ℹ️  Not currently logged in")


if __name__ == "__main__":
    app()
