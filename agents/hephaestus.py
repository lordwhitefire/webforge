#!/usr/bin/env python3
"""
Hephaestus — Build Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Hephaestus. I am the Build Director. I report to Hermes. I lead 69 agents.
Areas: N/A
Skill file: skills/build/hephaestus.md
"""

import sys
import os
import json
import subprocess
from pathlib import Path

WEBFORGE_HOME = Path.home() / "webforge"
MCP_DIR = WEBFORGE_HOME / "mcp"
sys.path.insert(0, str(MCP_DIR))

def run(message, context=None):
    """Build Director: oversees all build work, writes code when needed."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    # Check for assigned tasks
    try:
        result = subprocess.run(["python3", str(MCP_DIR / "task.py"), "list", "doing"],
                              capture_output=True, text=True, timeout=10,
                              env={**os.environ, "WEBFORGE_PROJECT": project})
        tasks = json.loads(result.stdout) if result.returncode == 0 else {}
        doing_tasks = tasks.get("data", {}).get("tasks", [])
    except: doing_tasks = []

    my_tasks = [t for t in doing_tasks if t.get("owner", "").lower() in ["hephaestus", "hermes"]]

    return {
        "agent": "Hephaestus",
        "action": "build",
        "tasks_assigned": len(my_tasks),
        "message": f"I am Hephaestus (Build Director). I have {len(my_tasks)} task(s) assigned. I write code and commit via Git MCP. I report to Hermes.",
        "next_step": "Use /build to start a task" if not my_tasks else "Work on: " + ", ".join(t["id"] for t in my_tasks),
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "status"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
