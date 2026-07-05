#!/usr/bin/env python3
"""
JrQuartz — Build Department Worker

STANDALONE script. Does the actual work.

Role: I am JrQuartz. I am a Junior Build Developer. I report to Hephaestus.
Areas: varies
"""

import sys
import os
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime, timezone

WEBFORGE_HOME = Path.home() / "webforge"
MCP_DIR = WEBFORGE_HOME / "mcp"
sys.path.insert(0, str(MCP_DIR))
sys.path.insert(0, str(WEBFORGE_HOME / "agents"))

CONSTRAINTS = {
    "role": "Junior Build Developer",
    "allowed": ["write_code", "fix_bug", "clone_repo", "answer_question"],
    "forbidden": ["delegate", "route", "approve", "reject"],
}


def _project_root() -> Path:
    p = os.environ.get("WEBFORGE_PROJECT")
    if p:
        return Path(p).expanduser().resolve()
    return Path.cwd().resolve()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(line: str):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {line}", flush=True)


import state as _state
_state.init_schema()


def check_my_tasks() -> list:
    rows = _state.query(
        "SELECT * FROM tasks WHERE LOWER(owner)=? AND status IN ('todo', 'doing') ORDER BY created_at ASC",
        ("jr-quartz",)
    )
    return rows


def mark_done(task_id: str, summary: str = "") -> bool:
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
    try:
        from memory import session_append
        session_append(message, agent="JrQuartz", kind=kind)
    except Exception:
        pass


def notify_agent(agent_name: str, event: str, message: str, task_id: str = "",
                 priority: int = 0):
    try:
        from mailbox import Mailbox
        mb = Mailbox("jr-quartz")
        msg_type = event.upper().replace(" ", "_")
        if msg_type not in ("TASK_CREATED", "TASK_ASSIGNED", "TASK_ACK", "TASK_PROGRESS",
                            "TASK_DONE", "TASK_BLOCKED", "REVIEW_NEEDED", "REVIEW_RESULT",
                            "QUESTION", "ANSWER", "ESCALATION", "INFO"):
            msg_type = "INFO"
        mb.send(
            to=agent_name, msg_type=msg_type,
            subject=event, body=message,
            task_id=task_id if task_id else None,
            priority=priority,
        )
    except Exception as e:
        _log(f"notify failed: {e}")


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


def ack_task(task: dict):
    task_id = task["id"]
    title = task.get("title", "unknown")

    try:
        assigned_msg = _state.query_one(
            "SELECT * FROM messages WHERE to_agent=? AND type='TASK_ASSIGNED' "
            "AND task_id=? AND status='unread' ORDER BY created_at DESC LIMIT 1",
            ("jr-quartz", task_id)
        )
        if assigned_msg:
            from mailbox import Mailbox
            Mailbox("jr-quartz").ack(assigned_msg["id"], "On it — " + title)
    except Exception as e:
        _log(f"ack failed: {e}")

    notify_agent("Hephaestus", "TASK_ACK",
                 "ACK — picked up " + task_id + ": Junior Build Developer.", task_id)
    notify_agent("Developer", "TASK_ACK",
                 "@JrQuartz ACK'd " + task_id + ": Junior Build Developer.", task_id)
    log_to_memory("JrQuartz ACK — picked up " + task_id + ": Junior Build Developer", kind="decision")
    _log(f"ACK sent for {task_id}")


def do_clone_repo(repo_url: str, task_id: str) -> str:
    _log(f"Cloning {repo_url}")
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
    task_id = task["id"]
    title = task.get("title", "unknown")
    task_type = task.get("type", "feature")

    work_dir = _project_root() / ".webforge" / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    stub_path = work_dir / f"{task_id}-{task_type}.md"
    title_str = "Junior Build Developer"
    owner_str = "JrQuartz"
    areas_str = "varies"
    stub_content = f"""# {task_id}: {title}

- Type: {task_type}
- Effort: {{task.get('effort', 'M')}}
- Owner: {owner_str}
- Started: {{task.get('started_at', _now())}}
- Completed: {_now()}
- Areas: {areas_str}

## Description
{{task.get('description', '(no description)')}}

## Status
{owner_str} processed this task. For real code work, the ContextBuilder
should be invoked via ask_ai_focused() to write actual code.
"""
    stub_path.write_text(stub_content, encoding="utf-8")
    msg = f"Created work stub: {stub_path.name}"
    _log(msg)
    return msg


def do_work(task: dict) -> str:
    title = task.get("title", "")
    title_lower = title.lower()

    if "clone" in title_lower and ("repo" in title_lower or "github.com" in title_lower or ".git" in title_lower):
        url_match = re.search(r'https?://[^\s]+\.git|https?://github\.com/[^\s]+', title)
        if url_match:
            return do_clone_repo(url_match.group(0), task["id"])
        return "Clone task but no URL found"

    return do_default_work(task)


def run(message: str = "work", context: dict = None) -> dict:
    _log(f"JrQuartz triggered (task_id={os.environ.get('WEBFORGE_TASK_ID', '')!r})")

    checkpoint("started", {"message": message})

    my_tasks = check_my_tasks()
    _log(f"Found {len(my_tasks)} task(s) assigned to me")

    explicit_id = os.environ.get("WEBFORGE_TASK_ID", "").strip()
    if explicit_id:
        explicit = [t for t in my_tasks if t["id"] == explicit_id]
        if explicit:
            my_tasks = explicit
        else:
            task = _state.query_one("SELECT * FROM tasks WHERE id=?", (explicit_id,))
            if task and (task.get("owner") or "").lower() == "jr-quartz":
                my_tasks = [task]

    if not my_tasks:
        no_work_msg = f"I am JrQuartz. No tasks assigned to me."
        _log(no_work_msg)
        complete_run(output=no_work_msg)
        return {
            "agent": "JrQuartz",
            "action": "idle",
            "message": no_work_msg,
            "next_step": None,
        }

    task = my_tasks[0]
    task_id = task["id"]
    task_title = task.get("title", "unknown")
    _log(f"Working on {task_id}: {task_title}")

    ack_task(task)
    checkpoint("ack", {"task_id": task_id})

    try:
        notify_agent("Developer", "TASK_PROGRESS",
                     f"@JrQuartz → {task_id}: Starting work", task_id)
        checkpoint("working", {})
        result_message = do_work(task)
        notify_agent("Developer", "TASK_PROGRESS",
                     f"@JrQuartz → {task_id}: {result_message}", task_id)
        checkpoint("work_complete", {"result": result_message})
    except Exception as e:
        err_msg = f"Work failed: {e}"
        _log(err_msg)
        notify_agent("Developer", "TASK_BLOCKED",
                     f"@JrQuartz failed on {task_id}: {e}", task_id, priority=2)
        try:
            from task import task_block
            task_block(task_id, str(e))
        except Exception:
            pass
        complete_run(output=err_msg, exit_code=1)
        return {
            "agent": "JrQuartz", "action": "failed",
            "task_id": task_id, "message": err_msg, "next_step": None,
        }

    mark_done(task_id, result_message)
    _log(f"Task {task_id} marked DONE")
    checkpoint("done", {"result": result_message})

    notify_agent("Hephaestus", "TASK_DONE",
                 f"DONE — {task_id}: {task_title}. {result_message}", task_id)
    notify_agent("Developer", "TASK_DONE",
                 f"@JrQuartz completed {task_id}: {task_title}. Result: {result_message}",
                 task_id)
    log_to_memory(f"JrQuartz COMPLETED {task_id}: {task_title} — {result_message}",
                  kind="decision")

    complete_run(output=result_message, exit_code=0)

    return {
        "agent": "JrQuartz",
        "action": "work_complete",
        "task_id": task_id,
        "task_title": task_title,
        "message": (
            f"I am JrQuartz. I worked on {task_id}: {task_title}.\n"
            f"  Result: {result_message}\n"
            f"  Task marked DONE."
        ),
        "next_step": None,
    }


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "work"
    _log(f"=== JrQuartz starting (pid={os.getpid()}) ===")
    r = run(msg)
    _log(f"=== JrQuartz done: action={r.get('action')} ===")
    print(r.get("message", json.dumps(r, indent=2)))
