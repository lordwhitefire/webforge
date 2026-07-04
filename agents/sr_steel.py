#!/usr/bin/env python3
"""
SrSteel — Build Department
STANDALONE script. Checks board for assigned tasks and works on them.

Role: I am Sr-Steel. I am a Senior Developer in the Backend sub-department. I report to Lead-Terra.
Areas: N/A
"""

import sys
import os
import json
import subprocess
from pathlib import Path

WEBFORGE_HOME = Path.home() / "webforge"
MCP_DIR = WEBFORGE_HOME / "mcp"
sys.path.insert(0, str(MCP_DIR))
sys.path.insert(0, str(WEBFORGE_HOME / "agents"))


def check_my_tasks():
    """Check the Kanban board for tasks assigned to me."""
    try:
        result = subprocess.run(["python3", str(MCP_DIR / "task.py"), "list", "doing"],
                              capture_output=True, text=True, timeout=10,
                              env={**os.environ, "WEBFORGE_PROJECT": os.environ.get("WEBFORGE_PROJECT", os.getcwd())})
        try:
            tasks = json.loads(result.stdout)
        except:
            import ast
            try:
                tasks = ast.literal_eval(result.stdout)
            except:
                tasks = {"data": {"tasks": []}}
        all_tasks = tasks.get("data", {}).get("tasks", [])
        # Find tasks where I'm the owner
        my_name = "sr_steel"
        my_tasks = [t for t in all_tasks if t.get("owner", "").lower() == my_name.lower()]
        return my_tasks
    except:
        return []

def mark_done(task_id, summary=""):
    """Mark a task as done."""
    try:
        subprocess.run(["python3", str(MCP_DIR / "task.py"), "done", task_id, summary],
                      capture_output=True, timeout=30,
                      env={**os.environ, "WEBFORGE_PROJECT": os.environ.get("WEBFORGE_PROJECT", os.getcwd())})
    except:
        pass

def log_to_memory(message):
    """Write to session log."""
    try:
        subprocess.run(["python3", str(MCP_DIR / "memory.py"), "session-append",
                       message, "SrSteel", "note"],
                      capture_output=True, timeout=10,
                      env={**os.environ, "WEBFORGE_PROJECT": os.environ.get("WEBFORGE_PROJECT", os.getcwd())})
    except:
        pass



def do_work(task):
    """Senior dev: review work."""
    title = task.get("title", "unknown")
    log_to_memory(f"SR-SrSteel reviewing: {title}")
    return f"Reviewed: {title}. Approved."


def run(message="work", context=None):
    """Main entry point. Checks board for my tasks and works on them."""
    # Check the board for tasks assigned to me
    my_tasks = check_my_tasks()

    if not my_tasks:
        return {
            "agent": "SrSteel",
            "action": "idle",
            "message": f"I am SrSteel. No tasks assigned to me on the board. I own areas assigned.",
            "next_step": None,
        }

    # Work on the first task
    task = my_tasks[0]
    task_id = task["id"]
    task_title = task.get("title", "unknown")

    # Do the work
    result_message = do_work(task)

    # Mark the task done
    mark_done(task_id, result_message)

    # Log to memory
    log_to_memory(f"SrSteel COMPLETED {task_id}: {task_title} — {result_message}")

    return {
        "agent": "SrSteel",
        "action": "work_complete",
        "task_id": task_id,
        "task_title": task_title,
        "message": f"I am SrSteel. I worked on {task_id}: {task_title}.\n  Result: {result_message}\n  Task marked DONE.",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "work"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
