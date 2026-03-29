# sqlite-log-handler-template

A minimal, reusable SQLite-backed logging handler for Python CLI tools.

This is a **reference repo** — not a package. Read the files, adapt them into your project.

---

## What this is and why

Python's built-in `logging` module is synchronous. Disk writes on every log call add latency to CLI tools. This pattern moves all SQLite writes to a background daemon thread so `emit()` never blocks the caller.

Storing logs in SQLite rather than flat files gives you structured querying, per-run grouping, and a drop-in Typer command to browse them.

---

## How to use

1. Copy `sqlite_log_handler/log_handler.py` and `sqlite_log_handler/setup_logging.py` into your project.
2. Call `setup_logging()` at the top of each CLI command entry point.
3. Optionally copy `examples/logs_command.py` into your CLI and register it with Typer.

```python
from your_project.setup_logging import setup_logging

@app.command()
def sync() -> None:
    run_id = setup_logging(command="sync", db_path=DB_PATH)
    # all logging.* calls from here are persisted to SQLite
    logging.info("Starting sync  run_id=%s", run_id)
```

---

## Log table schema

```sql
CREATE TABLE IF NOT EXISTS log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id    TEXT    NOT NULL,
    command   TEXT    NOT NULL,
    ts        TEXT    NOT NULL,  -- "YYYY-MM-DD HH:MM:SS.mmm"
    level     TEXT    NOT NULL,  -- "INFO", "ERROR", etc.
    level_no  INTEGER NOT NULL,  -- 10, 20, 30, 40, 50
    logger    TEXT    NOT NULL,  -- record.name
    module    TEXT    NOT NULL,
    func      TEXT    NOT NULL,
    lineno    INTEGER NOT NULL,
    message   TEXT    NOT NULL,
    exc_text  TEXT             -- NULL if no exception
);
```

Indexes on `run_id`, `ts`, `level_no`, `logger`, `command`.

---

## Example queries

### Raw SQL

```sql
-- All errors from the last run
SELECT ts, level, logger, message FROM log
WHERE run_id = '<uuid>' AND level_no >= 40
ORDER BY ts;

-- Runs summary
SELECT substr(run_id,1,8), command, min(ts), max(ts), count(*),
       sum(CASE WHEN level_no >= 40 THEN 1 ELSE 0 END)
FROM log GROUP BY run_id, command ORDER BY min(ts) DESC;
```

### Via the CLI (after adding `examples/logs_command.py`)

```bash
# All runs
myapp logs --runs

# Errors from a specific run
myapp logs --run-id a1b2c3d4 --errors-only

# Recent warnings from the sync command
myapp logs --command sync --level WARNING --since 2024-01-01
```

---

## Files

| File | Purpose |
|------|---------|
| `sqlite_log_handler/log_handler.py` | `SQLiteHandler` — non-blocking background-thread handler |
| `sqlite_log_handler/setup_logging.py` | `setup_logging()` — wires console + SQLite handlers, returns `run_id` |
| `examples/logs_command.py` | Drop-in Typer `logs` command with filtering and runs summary |
