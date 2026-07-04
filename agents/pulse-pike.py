#!/usr/bin/env python3
"""
PulsePike — Quality Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Pulse-Pike. I am a Bug Fixer Agent. I report to Pulse-Core.
Areas: 36-40
Skill file: skills/quality/pulse-pike.md
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
    """Pulse agent: fixes bugs for areas 36-40."""
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
        "agent": "PulsePike",
        "action": "fix_bugs",
        "areas": "36-40",
        "open_bugs": len(bugs),
        "message": f"I am PulsePike (Bug Fixer). I fix bugs in areas 36-40. There are {len(bugs)} open bug(s). I report to Pulse-Core.",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "fix bugs"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
