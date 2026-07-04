#!/usr/bin/env python3
"""
Thoth — Documentation Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Thoth. I am the Documentation Director. I report to Hermes. I lead 60 agents.
Areas: N/A
Skill file: skills/documentation/thoth.md
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
    """Documentation Director: generates docs from project state."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    return {
        "agent": "Thoth",
        "action": "generate_docs",
        "message": f"I am Thoth (Documentation Director). I generate README, changelog, API docs, env docs, and onboarding docs from project state. I report to Hermes.",
        "next_step": "Use /readme, /changelog, /api-docs, /env-docs, /onboard, or /docs",
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "docs"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
