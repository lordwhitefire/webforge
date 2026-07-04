#!/usr/bin/env python3
"""
JanusSlate — Quality Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Janus-Slate. I am a Security & Compliance Agent. I report to Janus-Core.
Areas: 26-30
Skill file: skills/quality/janus-slate.md
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
    """Janus agent: checks security and compliance for areas 26-30."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    return {
        "agent": "JanusSlate",
        "action": "security_check",
        "areas": "26-30",
        "message": f"I am JanusSlate (Security & Compliance). I check security vulnerabilities, NDPR/GDPR compliance, and accessibility (WCAG) for areas 26-30. I report to Janus-Core.",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "security check"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
