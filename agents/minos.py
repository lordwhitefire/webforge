#!/usr/bin/env python3
"""
Minos — Quality Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Minos. I am the Quality Director. I report to Hermes. I lead 108 agents.
Areas: N/A
Skill file: skills/quality/minos.md
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
    """Quality Director: runs quality checks and tracks bugs."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    # Run quality check
    try:
        result = subprocess.run(["python3", str(MCP_DIR / "quality.py"), "check"],
                              capture_output=True, text=True, timeout=60,
                              env={**os.environ, "WEBFORGE_PROJECT": project})
        check_ok = result.returncode == 0
    except: check_ok = False

    return {
        "agent": "Minos",
        "action": "quality_check",
        "check_passed": check_ok,
        "message": f"I am Minos (Quality Director). I run quality checks, track bugs, and review code. Quality check: {'PASSED' if check_ok else 'FAILED/CHECK NEEDED'}. I report to Hermes.",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "check"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
