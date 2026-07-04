#!/usr/bin/env python3
"""
LeadTerra — Build Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Lead-Terra. I am a Tech Lead in the Build team. I report to Titan.
Areas: N/A
Skill file: skills/build/lead_terra.md
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
    """Tech lead: manages senior developers, tracks progress."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    return {
        "agent": "LeadTerra",
        "action": "coordinate",
        "message": f"I am LeadTerra (Tech Lead). I manage senior developers and track build progress. I report to my department head.",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "status"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
