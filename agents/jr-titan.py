#!/usr/bin/env python3
"""
JrTitan — Build Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Jr-Titan. I am a Junior Backend Developer. I report to my Senior Developer.
Areas: 61-65
Skill file: skills/build/jr-titan.md
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
    """Build department head: oversees build sub-department."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    return {
        "agent": "JrTitan",
        "action": "oversee",
        "message": f"I am JrTitan (Build Sub-Head). I oversee my sub-department and report to Hephaestus.",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "status"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
