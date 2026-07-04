#!/usr/bin/env python3
"""
SrVance — Build Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Sr-Vance. I am a Senior Developer in the Frontend sub-department. I report to Lead-Faro.
Areas: N/A
Skill file: skills/build/sr_vance.md
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
    """Senior developer: reviews junior work and reports up."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    # Check for tasks to review
    try:
        result = subprocess.run(["python3", str(MCP_DIR / "task.py"), "list", "doing"],
                              capture_output=True, text=True, timeout=10,
                              env={**os.environ, "WEBFORGE_PROJECT": project})
        tasks = json.loads(result.stdout) if result.returncode == 0 else {}
        doing_tasks = tasks.get("data", {}).get("tasks", [])
    except: doing_tasks = []

    return {
        "agent": "SrVance",
        "action": "review",
        "message": f"I am SrVance (Senior Dev). I review junior developers' work. {len(doing_tasks)} task(s) in progress. I report to my Tech Lead.",
        "tasks_in_progress": len(doing_tasks),
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "review"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
