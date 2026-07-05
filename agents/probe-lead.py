#!/usr/bin/env python3
"""
Probe-Lead — Intelligence Department
Team Lead for the Probe Team. Reports to Athena. Manages all Probe-* agents.

Role: I am Probe-Lead. I am the Probe Team Lead in the Intelligence department. I report to Athena.
Areas: N/A
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

CONSTRAINTS = {
    "role": "Probe Team Lead — manages Probe agents, reports to Athena",
    "allowed": ["delegate", "review_code", "answer_question", "research"],
    "forbidden": ["write_code", "clone_repo", "fix_bug", "deploy"],
}


def _project_root():
    p = os.environ.get("WEBFORGE_PROJECT")
    if p:
        return Path(p).expanduser().resolve()
    return Path.cwd().resolve()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _log(line):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {line}", flush=True)


import state as _state
_state.init_schema()


def check_my_tasks():
    rows = _state.query(
        "SELECT * FROM tasks WHERE LOWER(owner)=? AND status IN ('todo', 'doing') ORDER BY created_at ASC",
        ("probe-lead",)
    )
    return rows


def log_to_memory(message, kind="note"):
    try:
        from memory import session_append
        session_append(message, agent="Probe-Lead", kind=kind)
    except Exception:
        pass


def notify_agent(agent_name, event, message, task_id="", priority=0):
    try:
        from mailbox import Mailbox
        mb = Mailbox("Probe-Lead")
        msg_type = event.upper().replace(" ", "_")
        if msg_type not in ("TASK_CREATED", "TASK_ASSIGNED", "TASK_ACK", "TASK_PROGRESS",
                            "TASK_DONE", "TASK_BLOCKED", "REVIEW_NEEDED", "REVIEW_RESULT",
                            "QUESTION", "ANSWER", "ESCALATION", "INFO"):
            msg_type = "INFO"
        bypass = agent_name.lower() in ("developer", "ceo")
        mb.send(to=agent_name, msg_type=msg_type, subject=event, body=message,
                task_id=task_id if task_id else None, priority=priority, bypass_chain=bypass)
    except ValueError as e:
        _log(f"CHAIN VIOLATION: {str(e)[:150]}")
    except Exception as e:
        _log(f"notify failed: {e}")


def run(message="work", context=None):
    _log(f"Probe-Lead triggered (task_id={os.environ.get('WEBFORGE_TASK_ID', '')!r})")

    my_tasks = check_my_tasks()
    _log(f"Found {len(my_tasks)} task(s)")

    if not my_tasks:
        return {"agent": "Probe-Lead", "action": "idle",
                "message": "I am Probe-Lead. No tasks assigned to me.", "next_step": None}

    # As a lead, delegate to probe-* workers
    task = my_tasks[0]
    task_id = task["id"]
    title = task.get("title", "unknown")
    _log(f"Delegating {task_id}: {title}")

    # ACK to Athena (direct superior)
    notify_agent("Athena", "TASK_ACK", f"ACK — received {task_id}. Delegating to Probe team.", task_id)

    # Pick a probe worker (round-robin for now)
    probe_workers = [f"probe-{n}" for n in [
        "orion", "wren", "beacon", "sable", "quartz", "flint", "ridge",
        "marsh", "coral", "vale", "thorne", "brisk", "hollow", "crag",
        "drift", "ember", "lyric",
    ]]
    worker = probe_workers[0]  # simple: pick first

    # Re-assign task
    try:
        from task import task_pick
        task_pick(task_id, worker, bypass_gate=True)
    except Exception as e:
        _log(f"task_pick failed: {e}")

    # Send mailbox message to worker (LEGAL — direct subordinate)
    try:
        from mailbox import Mailbox
        Mailbox("Probe-Lead").send(
            to=worker, msg_type="TASK_ASSIGNED",
            subject=f"Delegated: {title[:60]}",
            body=f"@Probe-Lead delegated task {task_id} to you.",
            task_id=task_id, priority=1,
        )
    except Exception as e:
        _log(f"send failed: {e}")

    # Trigger worker script
    try:
        worker_script = WEBFORGE_HOME / "agents" / f"{worker}.py"
        if worker_script.exists():
            env = os.environ.copy()
            env["WEBFORGE_PROJECT"] = str(_project_root())
            env["WEBFORGE_TASK_ID"] = task_id
            subprocess.Popen(["python3", str(worker_script), "work"],
                           stdout=open(_project_root() / ".webforge" / "logs" / f"{worker}.log", "w"),
                           stderr=subprocess.STDOUT, env=env, start_new_session=True)
    except Exception:
        pass

    return {
        "agent": "Probe-Lead", "action": "delegated",
        "task_id": task_id, "delegated_to": worker,
        "message": f"I am Probe-Lead. Delegated {task_id} to @{worker}.",
        "next_step": None,
    }


if __name__ == "__main__":
    r = run(" ".join(sys.argv[1:]) or "work")
    print(r.get("message", json.dumps(r, indent=2)))
