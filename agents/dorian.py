#!/usr/bin/env python3
"""
Dorian — Intelligence Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Dorian. I am the UI Researcher. I report to Athena.
Areas: N/A
Skill file: skills/intelligence/dorian.md
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
    """UI Researcher: researches UI/UX design references."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    return {
        "agent": "Dorian",
        "action": "research_ui",
        "message": f"I am Dorian (UI Researcher). I find UI/UX design references on the internet. I report to Athena. Topic: {message}",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "research UI"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
