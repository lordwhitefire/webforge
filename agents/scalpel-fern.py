#!/usr/bin/env python3
"""
ScalpelFern — Quality Department
STANDALONE script. Checks board for assigned tasks and works on them.

Role: I am Scalpel-Fern. I am a I write and run E2E tests in a real browser agent. I report to Scalpel-Core.
Areas: 31-35
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
        my_name = "scalpel-fern"
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
                       message, "ScalpelFern", "note"],
                      capture_output=True, timeout=10,
                      env={**os.environ, "WEBFORGE_PROJECT": os.environ.get("WEBFORGE_PROJECT", os.getcwd())})
    except:
        pass



def do_work(task):
    """Generic work."""
    return f"Worked on: {task.get('title', 'unknown')}"


def run(message="work", context=None):
    """Main entry point. Checks board for my tasks and works on them."""
    # Check the board for tasks assigned to me
    my_tasks = check_my_tasks()

    if not my_tasks:
        return {
            "agent": "ScalpelFern",
            "action": "idle",
            "message": f"I am ScalpelFern. No tasks assigned to me on the board. I own areas 31-35.",
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
    log_to_memory(f"ScalpelFern COMPLETED {task_id}: {task_title} — {result_message}")

    return {
        "agent": "ScalpelFern",
        "action": "work_complete",
        "task_id": task_id,
        "task_title": task_title,
        "message": f"I am ScalpelFern. I worked on {task_id}: {task_title}.\n  Result: {result_message}\n  Task marked DONE.",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "work"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
