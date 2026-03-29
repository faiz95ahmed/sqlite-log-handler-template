"""Convenience function to wire up console + SQLite logging."""

import logging
import sys
import uuid
from pathlib import Path

from .log_handler import SQLiteHandler


def setup_logging(
    command: str,
    db_path: Path,
    log_level: str = "INFO",
    run_id: str | None = None,
) -> str:
    """Configure root logger with a StreamHandler and a SQLiteHandler.

    Args:
        command:   CLI command name (e.g. "sync", "inbox"). Stored with every log row.
        db_path:   Path to the SQLite database file.
        log_level: Logging level string — DEBUG, INFO, WARNING, ERROR, CRITICAL.
        run_id:    Unique identifier for this run. Auto-generated UUID if not provided.

    Returns:
        The run_id (auto-generated or provided).
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    formatter = logging.Formatter(fmt="%(asctime)s %(levelname)-8s %(name)s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(numeric_level)
    console.setFormatter(formatter)
    root.addHandler(console)

    sqlite_handler = SQLiteHandler(db_path=db_path, run_id=run_id, command=command, level=numeric_level)
    sqlite_handler.setFormatter(formatter)
    root.addHandler(sqlite_handler)

    root.info("=" * 60)
    root.info("Logging initialised  level=%s  run_id=%s  command=%s", log_level, run_id, command)
    root.info("=" * 60)

    return run_id
