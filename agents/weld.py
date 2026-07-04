#!/usr/bin/env python3
"""
Weld — Hr Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Weld. I am the Assignment Officer. I report to Voss.
Areas: N/A
Skill file: skills/hr/weld.md
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
    """HR agent: manages agent lifecycle."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    # List active workers
    try:
        result = subprocess.run(["python3", str(MCP_DIR / "hr.py"), "list"],
                              capture_output=True, text=True, timeout=10,
                              env={**os.environ, "WEBFORGE_PROJECT": project})
        workers = json.loads(result.stdout) if result.returncode == 0 else {}
    except: workers = {}

    return {
        "agent": "Weld",
        "action": "hr",
        "workers": workers.get("data", {}),
        "message": f"I am Weld (HR). I manage agent recruitment, activation, and termination. I report to Hermes/Voss.",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "status"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
