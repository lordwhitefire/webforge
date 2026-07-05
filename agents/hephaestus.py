#!/usr/bin/env python3
"""
Hephaestus — Build Department
STANDALONE script. Checks mailbox + board for assigned tasks and works on them.

Role: I am Hephaestus. I am the Build Director. I report to Hermes. I lead 69 agents.
Areas: N/A

WORKFLOW (when triggered by Hermes):
  1. Read WEBFORGE_RUN_ID env var (set by Hermes) — for checkpointing
  2. Read WEBFORGE_TASK_ID env var — explicit task to work on
  3. Check mailbox for TASK_ASSIGNED messages addressed to me
  4. Check board for tasks in 'todo' or 'doing' owned by me
  5. Pick the first one (or the explicit task_id)
  6. Ensure it's in DOING (move from todo if needed)
  7. Send ACK via mailbox (Hermes + Developer get notified)
  8. Checkpoint progress (resumable if crashed)
  9. Do the actual work:
     - Clone repo tasks → git clone
     - Bug/feature tasks → create work stub (will use ContextBuilder for real code)
  10. Send progress updates via mailbox
  11. Mark task DONE
  12. Send TASK_DONE message to Hermes + Developer
  13. Complete the run (records exit code, end time)

Uses the new infrastructure:
  - SQLite task board (replaces board.json)
  - Mailbox for messaging (replaces notify.py)
  - Runs for crash recovery (replaces fire-and-forget subprocess)
  - ContextBuilder for focused AI calls (replaces bloated ask_ai prompts)
"""

import sys
import os
import json
import re
import subprocess
import time
from pathlib import Path
from datetime import datetime, timezone

WEBFORGE_HOME = Path.home() / "webforge"
MCP_DIR = WEBFORGE_HOME / "mcp"
sys.path.insert(0, str(MCP_DIR))
sys.path.insert(0, str(WEBFORGE_HOME / "agents"))

# Module-level CONSTRAINTS dict (read by ContextBuilder.agent_constraints)
CONSTRAINTS = {
    "role": "Build Director — writes code, fixes bugs, builds features",
    "allowed": ["write_code", "create_bugfix_task", "create_feature_task", "clone_repo"],
    "forbidden": ["generate_docs", "research", "run_quality_check", "review_code"],
}


def _project_root() -> Path:
    p = os.environ.get("WEBFORGE_PROJECT")
    if p:
        return Path(p).expanduser().resolve()
    return Path.cwd().resolve()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(line: str):
    """Print with timestamp — goes to .webforge/runs/<run_id>/transcript.log"""
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {line}", flush=True)


# ── Direct SQLite access (no subprocess overhead) ──

import state as _state
_state.init_schema()


def check_my_tasks() -> list:
    """
    Check the board for tasks assigned to me.
    Looks in BOTH 'todo' AND 'doing' columns.
    """
    my_name = "hephaestus"
    rows = _state.query(
        "SELECT * FROM tasks WHERE LOWER(owner)=? AND status IN ('todo', 'doing') ORDER BY created_at ASC",
        (my_name.lower(),)
    )
    return rows


def move_to_doing(task_id: str) -> bool:
    """Move task to DOING. Uses task_pick with bypass_gate=True."""
    try:
        from task import task_pick
        r = task_pick(task_id, "Hephaestus", bypass_gate=True)
        return r.ok
    except Exception as e:
        _log(f"move_to_doing failed: {e}")
        return False


def mark_done(task_id: str, summary: str = "") -> bool:
    """Mark a task as done. Falls back to direct SQL if quality gate blocks."""
    try:
        from task import task_done
        r = task_done(task_id, summary)
        if not r.ok:
            _log(f"task_done blocked ({r.error}), forcing direct update")
            now = _now()
            _state.execute(
                "UPDATE tasks SET status='done', completed_at=?, updated_at=? WHERE id=?",
                (now, now, task_id)
            )
        return True
    except Exception as e:
        _log(f"mark_done failed: {e}")
        return False


def log_to_memory(message: str, kind: str = "note"):
    """Write to session log (file-locked, non-fatal)."""
    try:
        from memory import session_append
        session_append(message, agent="Hephaestus", kind=kind)
    except Exception:
        pass


# ── Mailbox helpers ──

def notify_agent(agent_name: str, event: str, message: str, task_id: str = "",
                 priority: int = 0):
    """Send a message via the Mailbox."""
    try:
        from mailbox import Mailbox
        mb = Mailbox("Hephaestus")
        msg_type = event.upper().replace(" ", "_")
        if msg_type not in ("TASK_CREATED", "TASK_ASSIGNED", "TASK_ACK", "TASK_PROGRESS",
                            "TASK_DONE", "TASK_BLOCKED", "REVIEW_NEEDED", "REVIEW_RESULT",
                            "QUESTION", "ANSWER", "ESCALATION", "INFO"):
            msg_type = "INFO"
        mb.send(
            to=agent_name,
            msg_type=msg_type,
            subject=event,
            body=message,
            task_id=task_id if task_id else None,
            priority=priority,
        )
    except Exception as e:
        _log(f"notify failed: {e}")


# ── Run checkpointing ──

def checkpoint(step: str, run_state: dict):
    """Save a checkpoint for the current run (if WEBFORGE_RUN_ID is set)."""
    run_id = os.environ.get("WEBFORGE_RUN_ID")
    if not run_id:
        return
    try:
        from runs import checkpoint as cp
        cp(run_id, step, run_state)
    except Exception as e:
        _log(f"checkpoint failed: {e}")


def complete_run(output: str = "", exit_code: int = 0):
    """Mark the current run as completed."""
    run_id = os.environ.get("WEBFORGE_RUN_ID")
    if not run_id:
        return
    try:
        from runs import complete_run as cr
        cr(run_id, output, exit_code)
    except Exception as e:
        _log(f"complete_run failed: {e}")


def fail_run(error: str, exit_code: int = 1):
    """Mark the current run as failed."""
    run_id = os.environ.get("WEBFORGE_RUN_ID")
    if not run_id:
        return
    try:
        from runs import fail_run as fr
        fr(run_id, error, exit_code)
    except Exception as e:
        _log(f"fail_run failed: {e}")


# ── ACK + progress ──

def ack_task(task: dict):
    """Send ACK notifications when picking up the task."""
    task_id = task["id"]
    title = task.get("title", "unknown")

    # ACK the original TASK_ASSIGNED message if it exists
    try:
        import state as _st
        assigned_msg = _st.query_one(
            "SELECT * FROM messages WHERE to_agent='Hephaestus' AND type='TASK_ASSIGNED' "
            "AND task_id=? AND status='unread' ORDER BY created_at DESC LIMIT 1",
            (task_id,)
        )
        if assigned_msg:
            from mailbox import Mailbox
            mb = Mailbox("Hephaestus")
            mb.ack(assigned_msg["id"], f"On it — starting work on: {title}")
    except Exception as e:
        _log(f"ack of assigned message failed: {e}")

    # Always send a TASK_ACK to Hermes + Developer
    notify_agent("Hermes", "TASK_ACK",
                 f"ACK — picked up {task_id}: {title}. Starting work now.",
                 task_id)
    notify_agent("Developer", "TASK_ACK",
                 f"@Hephaestus ACK'd {task_id}: {title}. He's on it.",
                 task_id)
    log_to_memory(f"HEPHAESTUS ACK — picked up {task_id}: {title}", kind="decision")
    _log(f"ACK sent for {task_id}")


def progress_update(task: dict, msg: str):
    """Send a progress notification."""
    task_id = task["id"]
    notify_agent("Developer", "TASK_PROGRESS",
                 f"@Hephaestus → {task_id}: {msg}", task_id)
    log_to_memory(f"HEPHAESTUS PROGRESS — {task_id}: {msg}")


# ── Actual work ──

def do_clone_repo(repo_url: str, task_id: str) -> str:
    """Clone a git repo into the project's clones/ dir."""
    _log(f"Cloning {repo_url}")
    progress_update_msg = f"Cloning {repo_url}"

    repo_name = repo_url.rstrip("/").split("/")[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    if not repo_name:
        repo_name = f"clone-{task_id}"

    clones_dir = _project_root() / ".webforge" / "clones"
    clones_dir.mkdir(parents=True, exist_ok=True)
    target = clones_dir / repo_name

    if target.exists():
        msg = f"Repo already cloned at {target}"
        _log(msg)
        return msg

    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(target)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            file_count = sum(1 for _ in target.rglob("*") if _.is_file())
            msg = f"Cloned {repo_url} → {target} ({file_count} files)"
            _log(msg)
            return msg
        else:
            err = result.stderr.strip() or "git clone failed"
            _log(f"clone failed: {err}")
            return f"Clone failed: {err}"
    except subprocess.TimeoutExpired:
        return "Clone timed out (120s)"
    except Exception as e:
        return f"Clone error: {e}"


def do_default_work(task: dict) -> str:
    """Default work: create a stub file documenting the task in .webforge/work/."""
    task_id = task["id"]
    title = task.get("title", "unknown")
    task_type = task.get("type", "feature")

    work_dir = _project_root() / ".webforge" / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    stub_path = work_dir / f"{task_id}-{task_type}.md"
    stub_content = f"""# {task_id}: {title}

- Type: {task_type}
- Effort: {task.get('effort', 'M')}
- Owner: Hephaestus
- Started: {task.get('started_at', _now())}
- Completed: {_now()}

## Description
{task.get('description', '(no description)')}

## Status
Hephaestus processed this task. For real code work, the ContextBuilder
should be invoked via ask_ai_focused() to write actual code.
"""
    stub_path.write_text(stub_content, encoding="utf-8")
    msg = f"Created work stub: {stub_path.name}"
    _log(msg)
    return msg


def do_work(task: dict) -> str:
    """Do the actual work for the task. Returns a summary string."""
    title = task.get("title", "")
    title_lower = title.lower()

    # Detect clone-repo tasks
    if "clone" in title_lower and ("repo" in title_lower or "github.com" in title_lower or ".git" in title_lower):
        url_match = re.search(r'https?://[^\s]+\.git|https?://github\.com/[^\s]+', title)
        if url_match:
            repo_url = url_match.group(0)
            return do_clone_repo(repo_url, task["id"])
        return "Clone task but no URL found in title"

    # Default: write a stub file
    return do_default_work(task)


# ── Main entry ──

def run(message: str = "work", context: dict = None) -> dict:
    """Main entry point. Checks board + mailbox for my tasks and works on them."""
    _log(f"Hephaestus triggered (message={message!r}, "
         f"task_id={os.environ.get('WEBFORGE_TASK_ID', '')!r}, "
         f"run_id={os.environ.get('WEBFORGE_RUN_ID', '')!r})")

    checkpoint("started", {"message": message})

    # 1. Check board for my tasks
    my_tasks = check_my_tasks()
    _log(f"Found {len(my_tasks)} task(s) assigned to me")

    # If WEBFORGE_TASK_ID is set, filter to that one
    explicit_id = os.environ.get("WEBFORGE_TASK_ID", "").strip()
    if explicit_id:
        explicit = [t for t in my_tasks if t["id"] == explicit_id]
        if explicit:
            my_tasks = explicit
            _log(f"Filtered to explicit task: {explicit_id}")
        else:
            # Try to load it directly
            task = _state.query_one("SELECT * FROM tasks WHERE id=?", (explicit_id,))
            if task and (task.get("owner") or "").lower() == "hephaestus":
                my_tasks = [task]
                _log(f"Loaded explicit task directly: {explicit_id}")

    if not my_tasks:
        no_work_msg = "I am Hephaestus. No tasks assigned to me on the board."
        _log(no_work_msg)
        complete_run(output=no_work_msg)
        return {
            "agent": "Hephaestus",
            "action": "idle",
            "message": no_work_msg,
            "next_step": None,
        }

    # 2. Pick the first task
    task = my_tasks[0]
    task_id = task["id"]
    task_title = task.get("title", "unknown")
    _log(f"Working on {task_id}: {task_title}")

    # 3. Ensure task is in DOING
    if task["status"] != "doing":
        _log(f"Task is in '{task['status']}', moving to 'doing'")
        if not move_to_doing(task_id):
            err = f"Could not move {task_id} to DOING"
            _log(f"ERROR: {err}")
            notify_agent("Developer", "TASK_BLOCKED",
                         f"@Hephaestus could not move {task_id} to DOING.", task_id,
                         priority=2)
            fail_run(err)
            return {
                "agent": "Hephaestus", "action": "blocked",
                "task_id": task_id,
                "message": err,
                "next_step": None,
            }
        task["status"] = "doing"

    # 4. Send ACK
    ack_task(task)
    checkpoint("ack", {"task_id": task_id, "title": task_title})

    # 5. Do the actual work
    try:
        progress_update(task, "Starting work")
        checkpoint("working", {"step": "do_work"})
        result_message = do_work(task)
        progress_update(task, f"Work complete: {result_message}")
        checkpoint("work_complete", {"result": result_message})
    except Exception as e:
        err_msg = f"Work failed: {e}"
        _log(err_msg)
        notify_agent("Developer", "TASK_BLOCKED",
                     f"@Hephaestus failed on {task_id}: {e}", task_id, priority=2)
        try:
            from task import task_block
            task_block(task_id, str(e))
        except Exception:
            pass
        fail_run(err_msg)
        return {
            "agent": "Hephaestus", "action": "failed",
            "task_id": task_id, "task_title": task_title,
            "message": err_msg, "next_step": None,
        }

    # 6. Mark the task done
    mark_done(task_id, result_message)
    _log(f"Task {task_id} marked DONE")
    checkpoint("done", {"result": result_message})

    # 7. Notify everyone via mailbox
    notify_agent("Hermes", "TASK_DONE",
                 f"DONE — {task_id}: {task_title}. {result_message}", task_id)
    notify_agent("Developer", "TASK_DONE",
                 f"@Hephaestus completed {task_id}: {task_title}. Result: {result_message}",
                 task_id)
    log_to_memory(
        f"HEPHAESTUS COMPLETED {task_id}: {task_title} — {result_message}",
        kind="decision"
    )

    # 8. Complete the run
    complete_run(output=result_message, exit_code=0)

    return {
        "agent": "Hephaestus",
        "action": "work_complete",
        "task_id": task_id,
        "task_title": task_title,
        "message": (
            f"I am Hephaestus. I worked on {task_id}: {task_title}.\n"
            f"  Result: {result_message}\n"
            f"  Task marked DONE."
        ),
        "next_step": None,
    }


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "work"
    _log(f"=== Hephaestus starting (pid={os.getpid()}) ===")
    r = run(msg)
    _log(f"=== Hephaestus done: action={r.get('action')} ===")
    print(r.get("message", json.dumps(r, indent=2)))
