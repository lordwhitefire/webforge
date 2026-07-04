#!/usr/bin/env python3
"""
VerdictClove — Quality Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Verdict-Clove. I am a Standards Compliance Agent. I report to Minos.
Areas: 36-40
Skill file: skills/quality/verdict-clove.md
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
    """Verdict agent: checks standards compliance for areas 36-40."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    # Read rules
    try:
        result = subprocess.run(["python3", str(MCP_DIR / "memory.py"), "read-rules"],
                              capture_output=True, text=True, timeout=10,
                              env={**os.environ, "WEBFORGE_PROJECT": project})
        rules = result.stdout.strip() if result.returncode == 0 else "(no rules)"
    except: rules = "(no rules)"

    return {
        "agent": "VerdictClove",
        "action": "standards_check",
        "areas": "36-40",
        "rules": rules[:500],
        "message": f"I am VerdictClove (Standards Compliance). I check areas 36-40 against project standards and rules. I report to Minos.",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "check standards"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
