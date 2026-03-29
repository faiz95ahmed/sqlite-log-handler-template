"""Drop-in Typer `logs` CLI command.

Copy this file into your project and register it:

    app.command()(logs)

Replace the `DB_PATH` variable at the top with your project's database path,
or change the function signature to accept it as an argument.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

# ── Configure this for your project ──────────────────────────────────────────
DB_PATH = Path("app.db")
# ─────────────────────────────────────────────────────────────────────────────


def logs(
    limit: int = typer.Option(100, "--limit", "-l", help="Max rows to show"),
    level: Optional[str] = typer.Option(None, "--level", help="DEBUG|INFO|WARNING|ERROR"),
    module: Optional[str] = typer.Option(None, "--module", "-m", help="Prefix match on logger name"),
    command_filter: Optional[str] = typer.Option(None, "--command", "-c", help="Filter by command name"),
    run_id: Optional[str] = typer.Option(None, "--run-id", "-r", help="Prefix match on run_id"),
    since: Optional[datetime] = typer.Option(
        None,
        "--since",
        "-s",
        formats=["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"],
        help="Only show logs after this datetime",
    ),
    until: Optional[datetime] = typer.Option(
        None,
        "--until",
        "-u",
        formats=["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"],
        help="Only show logs before this datetime",
    ),
    errors_only: bool = typer.Option(False, "--errors-only", "-e", help="Only show ERROR+ rows"),
    runs: bool = typer.Option(False, "--runs", help="Show runs summary instead of log lines"),
) -> None:
    """Query stored logs from the SQLite database."""
    try:
        conn = sqlite3.connect(str(DB_PATH))

        if runs:
            try:
                rows = conn.execute(
                    """
                    SELECT
                        substr(run_id, 1, 8) AS short_id,
                        command,
                        min(ts)              AS started_at,
                        max(ts)              AS ended_at,
                        count(*)             AS total_lines,
                        sum(CASE WHEN level_no >= 40 THEN 1 ELSE 0 END) AS error_count
                    FROM log
                    GROUP BY run_id, command
                    ORDER BY started_at DESC
                    """
                ).fetchall()
            except sqlite3.OperationalError:
                typer.echo("No log table found. Run a command first to create it.")
                return

            if not rows:
                typer.echo("No runs found.")
                return

            typer.echo(f"{'RUN_ID':<10} {'COMMAND':<20} {'STARTED':<20} {'ENDED':<20} {'LINES':>6} {'ERRORS':>6}")
            typer.echo("─" * 90)
            for short_id, cmd, started, ended, total, errors in rows:
                typer.echo(f"{short_id:<10} {cmd:<20} {str(started)[:19]:<20} {str(ended)[:19]:<20} {total:>6} {errors:>6}")
            return

        # Build parameterised WHERE clause
        conditions: list[str] = []
        params: list[object] = []

        if errors_only:
            conditions.append("level_no >= 40")
        elif level:
            level_no = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}.get(level.upper())
            if level_no is not None:
                conditions.append("level_no = ?")
                params.append(level_no)

        if module:
            conditions.append("logger LIKE ?")
            params.append(module + "%")

        if command_filter:
            conditions.append("command = ?")
            params.append(command_filter)

        if run_id:
            conditions.append("run_id LIKE ?")
            params.append(run_id + "%")

        if since:
            conditions.append("ts >= ?")
            params.append(since.strftime("%Y-%m-%d %H:%M:%S"))

        if until:
            conditions.append("ts <= ?")
            params.append(until.strftime("%Y-%m-%d %H:%M:%S"))

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        query = f"SELECT ts, level, logger, message, exc_text FROM log {where} ORDER BY ts ASC LIMIT ?"
        params.append(limit)

        try:
            rows = conn.execute(query, params).fetchall()
        except sqlite3.OperationalError:
            typer.echo("No log table found. Run a command first to create it.")
            return
        finally:
            conn.close()

        if not rows:
            typer.echo("No log entries found.")
            return

        for ts, lvl, lgr, message, exc_text in rows:
            typer.echo(f"{ts}  {lvl:<8} {lgr}  {message}")
            if exc_text:
                for line in exc_text.splitlines():
                    typer.echo(f"    {line}")

    except Exception as e:
        typer.echo(f"Error querying logs: {e}", err=True)
        raise typer.Exit(code=1)
