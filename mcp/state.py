#!/usr/bin/env python3
"""
WebForge State MCP — SQLite-backed persistent state.

Replaces the flat board.json + per-agent JSON inboxes with a single
SQLite database using WAL mode for concurrent readers + single writer.

Schema:
  tasks          — Kanban board (replaces board.json)
  runs           — Agent execution runs (for crash recovery)
  messages       — Inter-agent mailbox (replaces notify.py JSON files)
  decisions      — ADR-style decision log
  checkpoints    — Per-run state snapshots (for resume after crash)
  sequence_counters — Atomic ID generation

All WebForge state lives in <project>/.webforge/state/webforge.db.
Markdown memory (PROJECT.md, STATE.md, decisions/) is separate —
see mcp/memory_md.py.
"""

import os
import sys
import json
import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager

sys.path.insert(0, str(Path(__file__).parent))
from common import get_project_root, write_log, utc_now


# ── Connection management ──

_local = threading.local()  # thread-local connections


def state_dir() -> Path:
    """Directory holding the SQLite DB. Created if missing."""
    d = get_project_root() / ".webforge" / "state"
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    return state_dir() / "webforge.db"


def get_conn() -> sqlite3.Connection:
    """
    Get a thread-local SQLite connection with WAL mode.

    WAL (Write-Ahead Logging) allows:
      - Multiple concurrent readers
      - One writer at a time
      - Readers don't block writers, writers don't block readers
      - Survives app crashes (WAL is journaled)
    """
    if not hasattr(_local, "conn") or _local.conn is None:
        conn = sqlite3.connect(
            str(db_path()),
            timeout=30.0,           # wait up to 30s on lock
            isolation_level=None,    # autocommit mode; we manage txns explicitly
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        # WAL mode: concurrent readers + 1 writer, no reader/writer blocking
        conn.execute("PRAGMA journal_mode=WAL")
        # Normal sync — fast, safe against app crashes (not OS crashes)
        conn.execute("PRAGMA synchronous=NORMAL")
        # Foreign keys on
        conn.execute("PRAGMA foreign_keys=ON")
        # Busy timeout — wait instead of erroring on lock
        conn.execute("PRAGMA busy_timeout=30000")
        _local.conn = conn
    return _local.conn


def close_conn():
    """Close this thread's connection. Useful for tests."""
    if hasattr(_local, "conn") and _local.conn is not None:
        _local.conn.close()
        _local.conn = None


def init_schema():
    """Create all tables if they don't exist. Idempotent."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id              TEXT PRIMARY KEY,
            title           TEXT NOT NULL,
            description     TEXT DEFAULT '',
            type            TEXT NOT NULL,         -- feature, bugfix, refactor, test, docs
            area            TEXT DEFAULT '',
            effort          TEXT DEFAULT 'M',      -- S, M, L
            status          TEXT NOT NULL DEFAULT 'backlog',  -- backlog, todo, doing, done, blocked
            owner           TEXT,                  -- agent name or NULL
            blocked_by      TEXT DEFAULT '[]',     -- JSON array of task_ids
            block_reason    TEXT,
            created_at      TEXT NOT NULL,
            started_at      TEXT,
            completed_at    TEXT,
            updated_at      TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_owner  ON tasks(owner);
        CREATE INDEX IF NOT EXISTS idx_tasks_type   ON tasks(type);

        CREATE TABLE IF NOT EXISTS runs (
            id              TEXT PRIMARY KEY,       -- run-001, run-002, ...
            task_id         TEXT,
            agent           TEXT NOT NULL,
            pid             INTEGER,
            trigger         TEXT,                   -- who triggered: Hermes, Developer, ...
            status          TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed, suspended
            started_at      TEXT NOT NULL,
            ended_at        TEXT,
            exit_code       INTEGER,
            error           TEXT,
            run_dir         TEXT,                   -- path to .webforge/runs/<id>/
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        );
        CREATE INDEX IF NOT EXISTS idx_runs_task   ON runs(task_id);
        CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
        CREATE INDEX IF NOT EXISTS idx_runs_agent  ON runs(agent);

        CREATE TABLE IF NOT EXISTS messages (
            id              TEXT PRIMARY KEY,       -- msg-001, msg-002, ...
            parent_id       TEXT,                   -- for threading
            from_agent      TEXT NOT NULL,
            to_agent        TEXT NOT NULL,
            type            TEXT NOT NULL,          -- TASK_ASSIGNED, TASK_ACK, TASK_PROGRESS, etc.
            subject         TEXT DEFAULT '',
            body            TEXT NOT NULL,
            task_id         TEXT,
            priority        INTEGER DEFAULT 0,      -- 0=normal, 1=high, 2=urgent
            created_at      TEXT NOT NULL,
            read_at         TEXT,
            acked_at        TEXT,
            status          TEXT DEFAULT 'unread',  -- unread, read, acked, replied, archived
            FOREIGN KEY (task_id) REFERENCES tasks(id),
            FOREIGN KEY (parent_id) REFERENCES messages(id)
        );
        CREATE INDEX IF NOT EXISTS idx_msgs_to_status ON messages(to_agent, status);
        CREATE INDEX IF NOT EXISTS idx_msgs_task      ON messages(task_id);
        CREATE INDEX IF NOT EXISTS idx_msgs_parent    ON messages(parent_id);

        CREATE TABLE IF NOT EXISTS decisions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id         TEXT,
            agent           TEXT NOT NULL,
            decision        TEXT NOT NULL,
            rationale       TEXT,
            timestamp       TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        );
        CREATE INDEX IF NOT EXISTS idx_decisions_task ON decisions(task_id);

        CREATE TABLE IF NOT EXISTS checkpoints (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id          TEXT NOT NULL,
            step            TEXT NOT NULL,           -- e.g. "ack", "research", "execute", "verify"
            state_json      TEXT NOT NULL,
            timestamp       TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES runs(id)
        );
        CREATE INDEX IF NOT EXISTS idx_checkpoints_run ON checkpoints(run_id);

        CREATE TABLE IF NOT EXISTS sequence_counters (
            name            TEXT PRIMARY KEY,
            next_value      INTEGER NOT NULL DEFAULT 1
        );
    """)
    write_log("State", "System", "init_schema", {"db": str(db_path())})


@contextmanager
def transaction():
    """
    Context manager for a transaction. Auto-commits on success, rolls back on error.

    Uses BEGIN IMMEDIATE to acquire the write lock upfront. This avoids
    the "database is locked" error that happens when a deferred transaction
    tries to upgrade from a read lock to a write lock while another
    connection holds the write lock.

    With BEGIN IMMEDIATE + busy_timeout=30000, concurrent writers will
    queue and wait up to 30s for the lock instead of failing immediately.

    Usage:
        with transaction() as conn:
            conn.execute("UPDATE tasks SET status=? WHERE id=?", ...)
    """
    conn = get_conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def next_id(name: str, prefix: str = "") -> str:
    """
    Atomically get the next ID from a sequence counter.

    Args:
        name: counter name (e.g. "task", "run", "msg")
        prefix: optional prefix (e.g. "task-", "run-", "msg-")

    Returns:
        e.g. "task-001", "run-042", "msg-007"
    """
    with transaction() as conn:
        row = conn.execute(
            "SELECT next_value FROM sequence_counters WHERE name=?",
            (name,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO sequence_counters (name, next_value) VALUES (?, ?)",
                (name, 2)
            )
            n = 1
        else:
            n = row["next_value"]
            conn.execute(
                "UPDATE sequence_counters SET next_value=? WHERE name=?",
                (n + 1, name)
            )
    return f"{prefix}{n:03d}"


def query(sql: str, params: tuple = ()) -> list:
    """Run a SELECT and return list of dict rows."""
    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    """Run a SELECT and return one dict row, or None."""
    conn = get_conn()
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def execute(sql: str, params: tuple = ()) -> int:
    """Run an INSERT/UPDATE/DELETE inside a transaction. Returns lastrowid."""
    with transaction() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


def info() -> dict:
    return {
        "id": "m-state",
        "name": "State MCP",
        "tier": 1,
        "owner": "System",
        "job": "SQLite-backed persistent state. Replaces board.json + JSON inboxes. WAL mode for concurrency.",
        "db_path": str(db_path()),
    }


# ── CLI ──

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("State MCP — SQLite-backed state for WebForge")
        print("Usage: python state.py <command>")
        print()
        print("Commands:")
        print("  init          Create schema (idempotent)")
        print("  info          Show DB info")
        print("  stats         Show row counts per table")
        print("  query <sql>   Run a SELECT and print results as JSON")
        print("  reset         DROP all tables and recreate (DESTRUCTIVE)")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "init":
        init_schema()
        print(f"Schema initialized at {db_path()}")
    elif cmd == "info":
        print(f"DB path: {db_path()}")
        print(f"DB exists: {db_path().exists()}")
        if db_path().exists():
            print(f"DB size: {db_path().stat().st_size} bytes")
            wal = db_path().parent / f"{db_path().name}-wal"
            if wal.exists():
                print(f"WAL size: {wal.stat().st_size} bytes")
    elif cmd == "stats":
        init_schema()
        for table in ("tasks", "runs", "messages", "decisions", "checkpoints"):
            n = query_one(f"SELECT COUNT(*) AS n FROM {table}")["n"]
            print(f"  {table}: {n} rows")
    elif cmd == "query":
        if len(sys.argv) < 3:
            print("Usage: python state.py query 'SELECT * FROM tasks LIMIT 5'")
            sys.exit(1)
        init_schema()
        rows = query(sys.argv[2])
        print(json.dumps(rows, indent=2, default=str))
    elif cmd == "reset":
        # Destructive — used in tests
        if len(sys.argv) < 3 or sys.argv[2] != "CONFIRM":
            print("This will DROP all tables. Run: python state.py reset CONFIRM")
            sys.exit(1)
        conn = get_conn()
        for table in ("checkpoints", "decisions", "messages", "runs", "tasks", "sequence_counters"):
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        print("All tables dropped. Run 'python state.py init' to recreate.")
    else:
        print(f"Unknown command: {cmd}")
