#!/usr/bin/env python3
"""
DocBuildReed — Documentation Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Doc-Build-Reed. I am an Embedded Documentation Agent. I report to Thoth.
Areas: N/A
Skill file: skills/documentation/doc-build-reed.md
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
    """Embedded doc agent: records decisions in real time for areas assigned."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    # Log to memory
    try:
        subprocess.run(["python3", str(MCP_DIR / "memory.py"), "session-append",
                       f"DOC-DocBuildReed recording activity for areas assigned",
                       "DocBuildReed", "note"],
                      capture_output=True, timeout=10,
                      env={**os.environ, "WEBFORGE_PROJECT": project})
    except: pass

    return {
        "agent": "DocBuildReed",
        "action": "record",
        "areas": "",
        "message": f"I am DocBuildReed (Embedded Doc Agent). I record decisions in real time for areas assigned. I report to Thoth. I do NOT wait until the end (Law 6).",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "record"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
