#!/usr/bin/env python3
"""
WebForge Runs MCP — agent execution runs with crash recovery.

Every time an agent is triggered (Hermes assigns a task → spawns
hephaestus.py), a "run" is created. The run has:
  - A unique ID (run-001, run-002, ...)
  - A row in the `runs` SQLite table (status, pid, started_at, ended_at, ...)
  - A directory on disk: .webforge/runs/<run_id>/
    containing: run.json, input.json, state.json (checkpoints),
    output.md, transcript.log, opencode.log

The reaper runs on WebForge startup and:
  1. Finds runs with status='running' but whose pid is no longer alive
  2. Either resumes them (if checkpoint exists) or marks them 'failed'
  3. Moves orphaned tasks back to 'todo' or 'blocked'

This is what opencode-workflows does with suspended runs — they survive
session restarts because state is on disk, not in process memory.
"""

import os
import sys
import json
import signal
import subprocess
import time
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root
from memory import session_append
import state


# ── Paths ──

def runs_dir() -> Path:
    d = get_project_root() / ".webforge" / "runs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def run_dir(run_id: str) -> Path:
    d = runs_dir() / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── Run lifecycle ──

def create_run(task_id: str, agent: str, trigger: str = "Hermes",
               input_data: dict = None) -> dict:
    """
    Create a new run record. Does NOT spawn the agent — caller does that.

    Args:
        task_id: The task this run is working on (may be empty)
        agent: Agent name (e.g. "Hephaestus")
        trigger: Who triggered this run (e.g. "Hermes", "Developer")
        input_data: The input message/context for this run

    Returns:
        The run dict (id, task_id, agent, status, run_dir, ...)
    """
    state.init_schema()
    run_id = state.next_id("run", "run-")
    now = utc_now()
    rd = run_dir(run_id)

    with state.transaction() as conn:
        conn.execute(
            """INSERT INTO runs (id, task_id, agent, pid, trigger, status,
                                 started_at, ended_at, exit_code, error, run_dir)
               VALUES (?, ?, ?, NULL, ?, 'pending', ?, NULL, NULL, NULL, ?)""",
            (run_id, task_id, agent, trigger, now, str(rd))
        )

    # Write input.json
    (rd / "input.json").write_text(json.dumps({
        "run_id": run_id,
        "task_id": task_id,
        "agent": agent,
        "trigger": trigger,
        "input": input_data or {},
        "created_at": now,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    # Initialize state.json (checkpoint file)
    (rd / "state.json").write_text(json.dumps({
        "run_id": run_id,
        "step": "init",
        "started_at": now,
        "last_updated": now,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    # Initialize empty transcript + output files
    (rd / "transcript.log").write_text(f"=== Run {run_id} started {now} ===\n", encoding="utf-8")
    (rd / "output.md").write_text("", encoding="utf-8")

    write_log("Runs", agent, "create_run",
              {"run_id": run_id, "task_id": task_id, "trigger": trigger})

    return state.query_one("SELECT * FROM runs WHERE id=?", (run_id,))


def start_run(run_id: str, pid: int):
    """Mark a run as started (agent process spawned)."""
    now = utc_now()
    with state.transaction() as conn:
        cur = conn.execute(
            "UPDATE runs SET status='running', pid=?, started_at=? WHERE id=?",
            (pid, now, run_id)
        )
        if cur.rowcount == 0:
            raise ValueError(f"Run not found: {run_id}")
    write_log("Runs", "", "start_run",
              {"run_id": run_id, "pid": pid})


def checkpoint(run_id: str, step: str, run_state: dict):
    """
    Save a checkpoint for this run. Called by the agent after each
    significant step (ack, research, execute, verify).

    The checkpoint is written to:
      1. The runs/<run_id>/state.json file (latest state, human-readable)
      2. The checkpoints SQLite table (append-only history)
    """
    now = utc_now()
    rd = run_dir(run_id)

    # Update state.json (latest)
    state_data = {
        "run_id": run_id,
        "step": step,
        "state": run_state,
        "last_updated": now,
    }
    (rd / "state.json").write_text(
        json.dumps(state_data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8"
    )

    # Append to checkpoints table (history)
    state.execute(
        "INSERT INTO checkpoints (run_id, step, state_json, timestamp) VALUES (?, ?, ?, ?)",
        (run_id, step, json.dumps(run_state, default=str), now)
    )

    write_log("Runs", "", "checkpoint",
              {"run_id": run_id, "step": step})


def complete_run(run_id: str, output: str = "", exit_code: int = 0):
    """Mark a run as completed successfully."""
    now = utc_now()
    rd = run_dir(run_id)

    if output:
        (rd / "output.md").write_text(output, encoding="utf-8")

    with state.transaction() as conn:
        conn.execute(
            "UPDATE runs SET status='completed', ended_at=?, exit_code=?, error=NULL WHERE id=?",
            (now, exit_code, run_id)
        )

    write_log("Runs", "", "complete_run",
              {"run_id": run_id, "exit_code": exit_code})


def fail_run(run_id: str, error: str, exit_code: int = 1):
    """Mark a run as failed."""
    now = utc_now()
    rd = run_dir(run_id)

    # Append error to transcript
    with (rd / "transcript.log").open("a", encoding="utf-8") as f:
        f.write(f"\n=== Run {run_id} FAILED {now} ===\nError: {error}\n")

    with state.transaction() as conn:
        conn.execute(
            "UPDATE runs SET status='failed', ended_at=?, exit_code=?, error=? WHERE id=?",
            (now, exit_code, error, run_id)
        )

    write_log("Runs", "", "fail_run",
              {"run_id": run_id, "error": error, "exit_code": exit_code})


def get_run(run_id: str) -> dict | None:
    return state.query_one("SELECT * FROM runs WHERE id=?", (run_id,))


def list_runs(status: str = "all", agent: str = None, task_id: str = None) -> list:
    """List runs, optionally filtered."""
    sql = "SELECT * FROM runs WHERE 1=1"
    params = []
    if status != "all":
        sql += " AND status=?"
        params.append(status)
    if agent:
        sql += " AND agent=?"
        params.append(agent)
    if task_id:
        sql += " AND task_id=?"
        params.append(task_id)
    sql += " ORDER BY started_at DESC"
    return state.query(sql, tuple(params))


# ── The reaper — runs on startup to clean up orphaned runs ──

def _is_pid_alive(pid: int | None) -> bool:
    """Check if a process with this PID is currently running."""
    if pid is None:
        return False
    if pid <= 0:
        return False
    try:
        # signal 0 = "check if process exists" — doesn't actually send a signal
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False


def reap_orphans(resume: bool = False) -> dict:
    """
    Find runs with status='running' but whose pid is no longer alive.

    Args:
        resume: If True, attempt to resume orphaned runs by re-spawning
                the agent with --resume <run_id>. If False, just mark them
                as failed and unblock their tasks.

    Returns:
        Summary dict: {orphaned: [...], resumed: [...], failed: [...]}
    """
    state.init_schema()
    orphaned = []
    resumed = []
    failed = []

    running_runs = state.query(
        "SELECT * FROM runs WHERE status='running' ORDER BY started_at"
    )

    for run in running_runs:
        pid = run.get("pid")
        if _is_pid_alive(pid):
            continue  # Still running, leave alone

        orphaned.append(run["id"])
        run_id = run["id"]
        task_id = run.get("task_id")
        agent = run.get("agent")

        # Read the last checkpoint to see how far it got
        last_cp = state.query_one(
            "SELECT * FROM checkpoints WHERE run_id=? ORDER BY timestamp DESC LIMIT 1",
            (run_id,)
        )

        if resume and last_cp and task_id:
            # Try to resume — re-spawn the agent with --resume
            try:
                _resume_run(run, last_cp)
                resumed.append(run_id)
                continue
            except Exception as e:
                write_log("Runs", agent, "resume_failed",
                          {"run_id": run_id, "error": str(e)})

        # Mark as failed
        fail_run(run_id, f"Agent process died (pid={pid}), no resume attempted")
        failed.append(run_id)

        # Unblock the task — move it back to 'todo' so another agent can pick it up
        if task_id:
            try:
                from task import task_block
                task_block(task_id, f"Agent {agent} crashed mid-run (run {run_id})")
            except Exception as e:
                write_log("Runs", agent, "task_unblock_failed",
                          {"run_id": run_id, "task_id": task_id, "error": str(e)})

    summary = {
        "orphaned": orphaned,
        "resumed": resumed,
        "failed": failed,
        "total": len(orphaned),
    }

    if orphaned:
        write_log("Runs", "Reaper", "reap_orphans", summary)
        session_append(
            f"REAPER — found {len(orphaned)} orphaned runs: "
            f"{len(resumed)} resumed, {len(failed)} failed",
            agent="Reaper", kind="note"
        )

    return summary


def _resume_run(run: dict, last_checkpoint: dict):
    """Re-spawn an agent process to resume a crashed run."""
    run_id = run["id"]
    agent = run["agent"]
    task_id = run.get("task_id")

    # Find the agent script
    agent_script = Path.home() / "webforge" / "agents" / f"{agent.lower()}.py"
    if not agent_script.exists():
        raise FileNotFoundError(f"Agent script not found: {agent_script}")

    env = os.environ.copy()
    env["WEBFORGE_PROJECT"] = str(get_project_root())
    env["WEBFORGE_TASK_ID"] = task_id or ""
    env["WEBFORGE_RUN_ID"] = run_id
    env["WEBFORGE_RESUME"] = "1"

    # Append to existing transcript
    rd = run_dir(run_id)
    with (rd / "transcript.log").open("a", encoding="utf-8") as f:
        f.write(f"\n=== Resuming run {run_id} ===\n")

    log_fp = open(rd / "transcript.log", "a")
    proc = subprocess.Popen(
        ["python3", str(agent_script), "work", "--resume", run_id],
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
    )

    # Update the run record with the new pid
    start_run(run_id, proc.pid)


# ── CLI ──

def info() -> dict:
    return {
        "id": "m-runs",
        "name": "Runs MCP",
        "tier": 1,
        "owner": "System",
        "job": "Agent execution runs with crash recovery. Every agent spawn gets a run record + on-disk state for resume.",
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Runs MCP — agent execution runs with crash recovery")
        print("Usage: python runs.py <command>")
        print()
        print("Commands:")
        print("  list [status]                List runs (all/running/completed/failed)")
        print("  show <run_id>                Show run details")
        print("  reap [--resume]              Reap orphaned runs (mark failed or resume)")
        print("  stats                        Show run statistics")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "list":
        status = sys.argv[2] if len(sys.argv) > 2 else "all"
        runs = list_runs(status)
        for r in runs:
            print(f"  {r['id']}: agent={r['agent']} task={r['task_id']} "
                  f"status={r['status']} pid={r.get('pid')}")
        print(f"\nTotal: {len(runs)} runs")
    elif cmd == "show":
        if len(sys.argv) < 3:
            print("Usage: python runs.py show <run_id>")
            sys.exit(1)
        run = get_run(sys.argv[2])
        if run is None:
            print(f"Run not found: {sys.argv[2]}")
            sys.exit(1)
        print(json.dumps(run, indent=2, default=str))
        # Also show last checkpoint
        cp = state.query_one(
            "SELECT * FROM checkpoints WHERE run_id=? ORDER BY timestamp DESC LIMIT 1",
            (sys.argv[2],)
        )
        if cp:
            print("\nLast checkpoint:")
            print(f"  step: {cp['step']}")
            print(f"  timestamp: {cp['timestamp']}")
            print(f"  state: {cp['state_json'][:200]}")
    elif cmd == "reap":
        resume = "--resume" in sys.argv
        summary = reap_orphans(resume=resume)
        print(f"Reaper summary:")
        print(f"  Orphaned found: {len(summary['orphaned'])}")
        print(f"  Resumed: {len(summary['resumed'])}")
        print(f"  Failed: {len(summary['failed'])}")
        if summary['orphaned']:
            print(f"  IDs: {summary['orphaned']}")
    elif cmd == "stats":
        for status in ("pending", "running", "completed", "failed", "suspended"):
            n = state.query_one(
                "SELECT COUNT(*) AS n FROM runs WHERE status=?", (status,)
            )["n"]
            print(f"  {status}: {n}")
    else:
        print(f"Unknown command: {cmd}")
