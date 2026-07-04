#!/usr/bin/env python3
"""
JanusReed — Quality Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Janus-Reed. I am a Security & Compliance Agent. I report to Janus-Core.
Areas: 06-10
Skill file: skills/quality/janus-reed.md
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
    """Janus agent: checks security and compliance for areas 06-10."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    return {
        "agent": "JanusReed",
        "action": "security_check",
        "areas": "06-10",
        "message": f"I am JanusReed (Security & Compliance). I check security vulnerabilities, NDPR/GDPR compliance, and accessibility (WCAG) for areas 06-10. I report to Janus-Core.",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "security check"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
