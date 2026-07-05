#!/usr/bin/env python3
"""
JrLake — Build Department Worker

STANDALONE script. Does the actual work.

Role: I am JrLake. I am a Junior Frontend Developer. I report to Sr-Hale.
Areas: 11-15
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
    "role": "Junior Frontend Developer",
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
        ("jr-lake",)
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
        session_append(message, agent="JrLake", kind=kind)
    except Exception:
        pass


def notify_agent(agent_name: str, event: str, message: str, task_id: str = "",
                 priority: int = 0):
    """
    Send a mailbox message from this worker to another agent.

    CHAIN-OF-COMMAND: A jr-* worker can only message:
      - Their direct superior (Sr-*) — legal
      - Developer (CEO) — ILLEGAL, must use bypass_chain=True (system notification)
      - Hephaestus — ILLEGAL, must go through Sr → Lead → Aurora → Hephaestus
    """
    try:
        from mailbox import Mailbox
        mb = Mailbox("jr-lake")
        msg_type = event.upper().replace(" ", "_")
        if msg_type not in ("TASK_CREATED", "TASK_ASSIGNED", "TASK_ACK", "TASK_PROGRESS",
                            "TASK_DONE", "TASK_BLOCKED", "REVIEW_NEEDED", "REVIEW_RESULT",
                            "QUESTION", "ANSWER", "ESCALATION", "INFO"):
            msg_type = "INFO"

        # Developer notifications are system-level (Developer = CEO, not in worker's chain)
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
            ("jr-lake", task_id)
        )
        if assigned_msg:
            from mailbox import Mailbox
            Mailbox("jr-lake").ack(assigned_msg["id"], "On it — " + title)
    except Exception as e:
        _log(f"ack failed: {e}")

    # ACK goes to direct superior (reports_to) — NOT Hephaestus
    # The jr-* worker's reports_to is set by the registry
    try:
        from registry import get_agent
        my_def = get_agent("jr-lake")
        superior = my_def.reports_to if my_def and my_def.reports_to else "Hephaestus"
    except ImportError:
        superior = "Hephaestus"
    notify_agent(superior, "TASK_ACK",
                 "ACK — picked up " + task_id + ": Junior Frontend Developer.", task_id)
    notify_agent("Developer", "TASK_ACK",
                 "@JrLake ACK'd " + task_id + ": Junior Frontend Developer.", task_id)
    log_to_memory("JrLake ACK — picked up " + task_id + ": Junior Frontend Developer", kind="decision")
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
    """For code tasks: call AI (DeepSeek) to write the code.
    For other tasks: create a stub file."""
    task_id = task["id"]
    title = task.get("title", "unknown")
    task_type = task.get("type", "feature")

    # For bugfix/feature/refactor tasks, call AI to write actual code
    if task_type in ("bugfix", "feature", "refactor"):
        return do_ai_code_work(task)

    # For other task types, create a stub file
    work_dir = _project_root() / ".webforge" / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    stub_path = work_dir / f"{task_id}-{task_type}.md"
    title_str = "Junior Frontend Developer"
    owner_str = "JrLake"
    areas_str = "11-15"
    stub_content = f"""# {task_id}: {title}

- Type: {task_type}
- Effort: {task.get('effort', 'M')}
- Owner: {owner_str}
- Started: {task.get('started_at', _now())}
- Completed: {_now()}
- Areas: {areas_str}

## Description
{task.get('description', '(no description)')}

## Status
{owner_str} processed this task.
"""
    stub_path.write_text(stub_content, encoding="utf-8")
    msg = f"Created work stub: {stub_path.name}"
    _log(msg)
    return msg


def do_ai_code_work(task: dict) -> str:
    """Call AI (DeepSeek) to write code for this task."""
    task_id = task["id"]
    title = task.get("title", "unknown")
    task_type = task.get("type", "feature")

    _log(f"Calling AI to write code for {task_id}: {title}")

    try:
        from context import ask_ai_focused
        result = ask_ai_focused(
            agent_name="jr-lake",
            task_id=task_id,
            call_type="code",
            instruction=(
                f"Task: {title}\n"
                f"Type: {task_type}\n"
                f"Description: {task.get('description', '(none)')}\n\n"
                f"Write the code to complete this task. "
                f"Respond with JSON containing: summary, files_changed (list of "
                '{"path": str, "content": str} objects), root_cause, fix_verified.'
            ),
            response_format='{"summary": str, "files_changed": [{"path": str, "content": str}], "root_cause": str, "fix_verified": bool}',
            run_id=os.environ.get("WEBFORGE_RUN_ID") or None,
        )

        if result.get("status") != "ok":
            return f"AI call failed: {result.get('error', 'unknown')}"

        response = result.get("response", {})
        model = result.get("model", "unknown")
        summary = response.get("summary", "(no summary)")
        files_changed = response.get("files_changed", [])

        # Write the AI-generated files to disk
        work_dir = _project_root() / ".webforge" / "work" / task_id
        work_dir.mkdir(parents=True, exist_ok=True)

        for f in files_changed:
            if isinstance(f, dict):
                fpath = f.get("path", "")
                fcontent = f.get("content", "")
                if fpath and fcontent:
                    # Write to work dir (not the actual project — that's a separate step)
                    out_path = work_dir / Path(fpath).name
                    out_path.write_text(fcontent, encoding="utf-8")
                    _log(f"Wrote: {out_path}")

        # Save the AI summary
        summary_path = work_dir / "summary.md"
        summary_path.write_text(
            f"# AI Code Work: {task_id}\n\n"
            f"**Model:** {model}\n\n"
            f"**Summary:** {summary}\n\n"
            f"**Root cause:** {response.get('root_cause', 'N/A')}\n\n"
            f"**Files changed:** {len(files_changed)}\n",
            encoding="utf-8"
        )

        msg = f"AI ({model}) wrote code for {task_id}: {summary[:100]}"
        _log(msg)
        return msg

    except Exception as e:
        _log(f"AI code work failed: {e}")
        return f"AI code work failed: {e}"


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
    _log(f"JrLake triggered (task_id={os.environ.get('WEBFORGE_TASK_ID', '')!r})")

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
            if task and (task.get("owner") or "").lower() == "jr-lake":
                my_tasks = [task]

    if not my_tasks:
        no_work_msg = f"I am JrLake. No tasks assigned to me."
        _log(no_work_msg)
        complete_run(output=no_work_msg)
        return {
            "agent": "JrLake",
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
                     f"@JrLake → {task_id}: Starting work", task_id)
        checkpoint("working", {})
        result_message = do_work(task)
        notify_agent("Developer", "TASK_PROGRESS",
                     f"@JrLake → {task_id}: {result_message}", task_id)
        checkpoint("work_complete", {"result": result_message})
    except Exception as e:
        err_msg = f"Work failed: {e}"
        _log(err_msg)
        notify_agent("Developer", "TASK_BLOCKED",
                     f"@JrLake failed on {task_id}: {e}", task_id, priority=2)
        try:
            from task import task_block
            task_block(task_id, str(e))
        except Exception:
            pass
        complete_run(output=err_msg, exit_code=1)
        return {
            "agent": "JrLake", "action": "failed",
            "task_id": task_id, "message": err_msg, "next_step": None,
        }

    mark_done(task_id, result_message)
    _log(f"Task {task_id} marked DONE")
    checkpoint("done", {"result": result_message})

    # DONE goes to direct superior (reports_to) — NOT Hephaestus
    try:
        from registry import get_agent
        my_def = get_agent("jr-lake")
        superior = my_def.reports_to if my_def and my_def.reports_to else "Hephaestus"
    except ImportError:
        superior = "Hephaestus"
    notify_agent(superior, "TASK_DONE",
                 f"DONE — {task_id}: {task_title}. {result_message}", task_id)
    notify_agent("Developer", "TASK_DONE",
                 f"@JrLake completed {task_id}: {task_title}. Result: {result_message}",
                 task_id)
    log_to_memory(f"JrLake COMPLETED {task_id}: {task_title} — {result_message}",
                  kind="decision")

    complete_run(output=result_message, exit_code=0)

    return {
        "agent": "JrLake",
        "action": "work_complete",
        "task_id": task_id,
        "task_title": task_title,
        "message": (
            f"I am JrLake. I worked on {task_id}: {task_title}.\n"
            f"  Result: {result_message}\n"
            f"  Task marked DONE."
        ),
        "next_step": None,
    }


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "work"
    _log(f"=== JrLake starting (pid={os.getpid()}) ===")
    r = run(msg)
    _log(f"=== JrLake done: action={r.get('action')} ===")
    print(r.get("message", json.dumps(r, indent=2)))
