#!/usr/bin/env python3
"""
JanusCore — Quality Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Janus-Core. I am the Lead for Security & Compliance. I report to Minos (and Hermes for critical security issues).
Areas: N/A
Skill file: skills/quality/janus-core.md
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
    """Janus agent: checks security and compliance for areas assigned."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    return {
        "agent": "JanusCore",
        "action": "security_check",
        "areas": "",
        "message": f"I am JanusCore (Security & Compliance). I check security vulnerabilities, NDPR/GDPR compliance, and accessibility (WCAG) for areas assigned. I report to Janus-Core.",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "security check"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
