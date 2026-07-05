#!/usr/bin/env python3
"""
Hephaestus — Build Department Director

STANDALONE script. DELEGATES work to subordinates — never does work himself.

Role: I am Hephaestus. I am the Build Director. I report to Hermes. I lead 69 agents.
I DO NOT write code. I DO NOT clone repos. I DO NOT fix bugs.
I DELEGATE to my subordinates (Aurora, Titan, Zephyr, and the 49 jr-* workers).

When triggered:
  1. Check mailbox for TASK_ASSIGNED messages
  2. Check board for tasks owned by me (in todo/doing)
  3. For each task:
     a. Send ACK to Hermes + Developer
     b. Use registry to pick the right worker for the task
     c. Re-assign the task to the worker (task_pick)
     d. Send TASK_ASSIGNED mailbox message to the worker
     e. Trigger the worker's script in background
     f. Send DELEGATED notification to Developer
  4. I do NOT mark the task done — the worker does that.

This is the CORRECT behavior for a director. The previous version of this
script had Hephaestus cloning repos himself, which was wrong — that's
worker work, not director work.
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

WEBFORGE_HOME = Path.home() / "webforge"
MCP_DIR = WEBFORGE_HOME / "mcp"
sys.path.insert(0, str(MCP_DIR))
sys.path.insert(0, str(WEBFORGE_HOME / "agents"))

# Module-level CONSTRAINTS dict (read by ContextBuilder.agent_constraints)
CONSTRAINTS = {
    "role": "Build Director — DELEGATES work to subordinates, never codes",
    "allowed": ["route", "delegate", "answer_question", "report_status"],
    "forbidden": [
        "write_code", "clone_repo", "fix_bug",
        "run_tests", "review_code", "write_docs",
        "research", "deploy",
    ],
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


# ── Direct SQLite access ──

import state as _state
_state.init_schema()


def check_my_tasks() -> list:
    """Check the board for tasks assigned to me (in todo or doing)."""
    rows = _state.query(
        "SELECT * FROM tasks WHERE LOWER(owner)=? AND status IN ('todo', 'doing') ORDER BY created_at ASC",
        ("hephaestus",)
    )
    return rows


def log_to_memory(message: str, kind: str = "note"):
    try:
        from memory import session_append
        session_append(message, agent="Hephaestus", kind=kind)
    except Exception:
        pass


def notify_agent(agent_name: str, event: str, message: str, task_id: str = "",
                 priority: int = 0):
    """
    Send a mailbox message from Hephaestus to another agent.

    CHAIN-OF-COMMAND: Hephaestus can only message:
      - Hermes (direct superior) — legal
      - Aurora, Titan, Zephyr (direct subordinates) — legal
      - Developer (CEO) — ILLEGAL, must use bypass_chain=True (system notification)
      - jr-* workers — ILLEGAL, must go through the chain
    """
    try:
        from mailbox import Mailbox
        mb = Mailbox("Hephaestus")
        msg_type = event.upper().replace(" ", "_")
        if msg_type not in ("TASK_CREATED", "TASK_ASSIGNED", "TASK_ACK", "TASK_PROGRESS",
                            "TASK_DONE", "TASK_BLOCKED", "REVIEW_NEEDED", "REVIEW_RESULT",
                            "QUESTION", "ANSWER", "ESCALATION", "INFO"):
            msg_type = "INFO"

        # Developer notifications are system-level (Developer = CEO, not in Hephaestus's chain)
        # Use bypass_chain=True for these
        bypass = agent_name.lower() in ("developer", "ceo")

        mb.send(
            to=agent_name, msg_type=msg_type,
            subject=event, body=message,
            task_id=task_id if task_id else None,
            priority=priority,
            bypass_chain=bypass,
        )
    except ValueError as e:
        _log(f"CHAIN VIOLATION in notify_agent: {str(e)[:150]}")
    except Exception as e:
        _log(f"notify failed: {e}")


# ── Run checkpointing ──

def checkpoint(step: str, run_state: dict):
    run_id = os.environ.get("WEBFORGE_RUN_ID")
    if not run_id:
        return
    try:
        from runs import checkpoint as cp
        cp(run_id, step, run_state)
    except Exception as e:
        _log(f"checkpoint failed: {e}")


def complete_run(output: str = "", exit_code: int = 0):
    run_id = os.environ.get("WEBFORGE_RUN_ID")
    if not run_id:
        return
    try:
        from runs import complete_run as cr
        cr(run_id, output, exit_code)
    except Exception as e:
        _log(f"complete_run failed: {e}")


# ── ACK + delegate ──

def ack_task(task: dict):
    """Send ACK notifications when picking up the task."""
    task_id = task["id"]
    title = task.get("title", "unknown")

    # ACK the original TASK_ASSIGNED message
    try:
        assigned_msg = _state.query_one(
            "SELECT * FROM messages WHERE to_agent='Hephaestus' AND type='TASK_ASSIGNED' "
            "AND task_id=? AND status='unread' ORDER BY created_at DESC LIMIT 1",
            (task_id,)
        )
        if assigned_msg:
            from mailbox import Mailbox
            Mailbox("Hephaestus").ack(assigned_msg["id"],
                                       f"ACK — delegating {task_id} to a worker")
    except Exception as e:
        _log(f"ack of assigned message failed: {e}")

    notify_agent("Hermes", "TASK_ACK",
                 f"ACK — received {task_id}: {title}. Delegating to a worker now.",
                 task_id)
    notify_agent("Developer", "TASK_ACK",
                 f"@Hephaestus ACK'd {task_id}: {title}. He's delegating to a worker.",
                 task_id)
    log_to_memory(f"HEPHAESTUS ACK — received {task_id}: {title}", kind="decision")
    _log(f"ACK sent for {task_id}")


def delegate_to_worker(task: dict) -> dict:
    """
    Delegate a task through the chain of command.

    HIERARCHY: Hephaestus → Aurora/Titan/Zephyr → Lead-* → Sr-* → Jr-*

    Hephaestus CANNOT message jr-* directly. He must:
      1. Determine which sub-department (Frontend/Backend/DB) the task belongs to
      2. Send TASK_DELEGATED to the appropriate lead (Aurora/Titan/Zephyr) via mailbox
      3. Use task_pick (system operation) to reassign the task to the final worker
      4. Trigger the worker's script (system operation)

    The mailbox message goes through the chain legally.
    The task ownership transfer and script trigger are system operations
    (not agent-to-agent messages) so they bypass the chain check.
    """
    task_id = task["id"]
    title = task.get("title", "unknown")
    task_type = task.get("type", "feature")

    try:
        from registry import pick_worker_for_task, get_agent
        worker = pick_worker_for_task(task)
        if worker is None:
            _log(f"No worker available for task type {task_type}")
            # Notify Developer (system notification, bypass chain)
            try:
                from mailbox import Mailbox
                Mailbox("Hephaestus").send(
                    to="Developer", msg_type="TASK_BLOCKED",
                    subject=f"No worker for {task_id}",
                    body=f"@Hephaestus could not find a worker for {task_id} (type: {task_type}).",
                    task_id=task_id, priority=2, bypass_chain=True,
                )
            except Exception:
                pass
            return {"ok": False, "error": f"No worker available for task type {task_type}"}

        worker_name = worker.name
        worker_title = worker.title
        worker_areas = worker.areas

        # Determine which lead to notify based on worker's sub-department
        title_lower = worker_title.lower()
        if "frontend" in title_lower:
            lead_name = "Aurora"
        elif "backend" in title_lower:
            lead_name = "Titan"
        elif "database" in title_lower or "infra" in title_lower:
            lead_name = "Zephyr"
        else:
            lead_name = "Aurora"  # default

        _log(f"Delegating {task_id}: Hephaestus → {lead_name} → ... → {worker_name}")

        # 1. Send TASK_DELEGATED to the direct subordinate lead (LEGAL chain)
        try:
            from mailbox import Mailbox
            mb = Mailbox("Hephaestus")
            mb.send(
                to=lead_name,
                msg_type="TASK_ASSIGNED",
                subject=f"Delegated: {title[:60]}",
                body=(
                    f"@Hephaestus delegated task {task_id} to your sub-department.\n"
                    f"Title: {title}\n"
                    f"Type: {task_type}\n"
                    f"Target worker: @{worker_name} ({worker_title})\n"
                    f"Worker areas: {worker_areas}\n\n"
                    f"Please delegate this down the chain to @{worker_name}."
                ),
                task_id=task_id,
                priority=1,
            )
        except ValueError as e:
            _log(f"CHAIN VIOLATION: {e}")
        except Exception as e:
            _log(f"mailbox send to lead failed: {e}")

        # 2. Re-assign the task to the final worker (SYSTEM operation, bypass chain)
        try:
            from task import task_pick
            task_pick(task_id, worker_name, bypass_gate=True)
        except Exception as e:
            _log(f"task_pick failed: {e}")

        # 3. Trigger the worker's script (SYSTEM operation, bypass chain)
        triggered = False
        try:
            worker_script = WEBFORGE_HOME / "agents" / f"{worker_name.lower()}.py"
            if worker_script.exists():
                env = os.environ.copy()
                env["WEBFORGE_PROJECT"] = str(_project_root())
                env["WEBFORGE_TASK_ID"] = task_id
                env["WEBFORGE_AGENT_TRIGGER"] = "Hephaestus"

                log_dir = _project_root() / ".webforge" / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                log_fp = open(log_dir / f"{worker_name.lower()}.log", "w")

                subprocess.Popen(
                    ["python3", str(worker_script), "work"],
                    stdout=log_fp,
                    stderr=subprocess.STDOUT,
                    env=env,
                    start_new_session=True,
                )
                triggered = True
                _log(f"Triggered @{worker_name} script")
        except Exception as e:
            _log(f"Failed to trigger worker script: {e}")

        # 4. Notify Developer of the delegation
        notify_agent("Developer", "TASK_PROGRESS",
                     f"@Hephaestus delegated {task_id} to @{worker_name} "
                     f"({worker_title}). Worker script triggered.",
                     task_id)

        return {
            "ok": True,
            "worker": worker_name,
            "worker_title": worker_title,
            "worker_areas": worker_areas,
            "triggered": triggered,
        }

    except ImportError:
        _log("registry not available — cannot delegate")
        return {"ok": False, "error": "registry not available"}
    except Exception as e:
        _log(f"delegation failed: {e}")
        return {"ok": False, "error": str(e)}


# ── Main entry ──

def run(message: str = "work", context: dict = None) -> dict:
    """
    Main entry point. As a DIRECTOR, I:
      1. Check my tasks
      2. For each task: ACK + delegate to a worker
      3. I do NOT do the work myself
    """
    _log(f"Hephaestus (Director) triggered (message={message!r}, "
         f"task_id={os.environ.get('WEBFORGE_TASK_ID', '')!r}, "
         f"run_id={os.environ.get('WEBFORGE_RUN_ID', '')!r})")

    checkpoint("started", {"message": message})

    # 1. Check board for my tasks
    my_tasks = check_my_tasks()
    _log(f"Found {len(my_tasks)} task(s) assigned to me")

    explicit_id = os.environ.get("WEBFORGE_TASK_ID", "").strip()
    if explicit_id:
        explicit = [t for t in my_tasks if t["id"] == explicit_id]
        if explicit:
            my_tasks = explicit
            _log(f"Filtered to explicit task: {explicit_id}")
        else:
            task = _state.query_one("SELECT * FROM tasks WHERE id=?", (explicit_id,))
            if task and (task.get("owner") or "").lower() == "hephaestus":
                my_tasks = [task]
                _log(f"Loaded explicit task directly: {explicit_id}")

    if not my_tasks:
        no_work_msg = ("I am Hephaestus, Build Director. "
                       "No tasks assigned to me on the board.")
        _log(no_work_msg)
        complete_run(output=no_work_msg)
        return {
            "agent": "Hephaestus",
            "action": "idle",
            "message": no_work_msg,
            "next_step": None,
        }

    # 2. Process each task — DELEGATE, don't do
    delegated = []
    for task in my_tasks:
        task_id = task["id"]
        task_title = task.get("title", "unknown")
        _log(f"Delegating {task_id}: {task_title}")

        # ACK
        ack_task(task)
        checkpoint("ack", {"task_id": task_id, "title": task_title})

        # Delegate to a worker
        checkpoint("delegating", {"task_id": task_id})
        result = delegate_to_worker(task)

        if result.get("ok"):
            delegated.append({
                "task_id": task_id,
                "worker": result["worker"],
                "worker_title": result["worker_title"],
            })
            checkpoint("delegated", result)
        else:
            _log(f"Delegation failed for {task_id}: {result.get('error')}")
            notify_agent("Developer", "TASK_BLOCKED",
                         f"@Hephaestus could not delegate {task_id}: "
                         f"{result.get('error', 'unknown')}",
                         task_id, priority=2)
            checkpoint("delegation_failed", result)

    # 3. Summarize
    summary_lines = [f"I am Hephaestus, Build Director."]
    summary_lines.append(f"Delegated {len(delegated)} task(s) to workers:")
    for d in delegated:
        summary_lines.append(f"  - {d['task_id']} → @{d['worker']} ({d['worker_title']})")
    summary_lines.append("")
    summary_lines.append("I do NOT do the work myself — that's my subordinates' job.")
    summary_lines.append("Watch the workers for progress.")

    summary = "\n".join(summary_lines)
    _log(f"Delegation complete: {len(delegated)} task(s)")

    complete_run(output=summary, exit_code=0)

    return {
        "agent": "Hephaestus",
        "action": "delegated",
        "delegated": delegated,
        "message": summary,
        "next_step": f"Watch the {len(delegated)} worker(s) for progress",
    }


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "work"
    _log(f"=== Hephaestus starting (pid={os.getpid()}) ===")
    r = run(msg)
    _log(f"=== Hephaestus done: action={r.get('action')} ===")
    print(r.get("message", json.dumps(r, indent=2)))
