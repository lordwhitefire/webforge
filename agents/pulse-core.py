#!/usr/bin/env python3
"""
PulseCore — Quality Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Pulse-Core. I am the Lead for Bug Fixing. I report to Minos.
Areas: N/A
Skill file: skills/quality/pulse-core.md
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
    """Pulse agent: fixes bugs for areas assigned."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    # Check for bug tasks
    try:
        result = subprocess.run(["python3", str(MCP_DIR / "bug.py"), "list"],
                              capture_output=True, text=True, timeout=10,
                              env={**os.environ, "WEBFORGE_PROJECT": project})
        bug_data = json.loads(result.stdout) if result.returncode == 0 else {}
        bugs = bug_data.get("data", {}).get("bugs", [])
    except: bugs = []

    return {
        "agent": "PulseCore",
        "action": "fix_bugs",
        "areas": "",
        "open_bugs": len(bugs),
        "message": f"I am PulseCore (Bug Fixer). I fix bugs in areas assigned. There are {len(bugs)} open bug(s). I report to Pulse-Core.",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "fix bugs"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
