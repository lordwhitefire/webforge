#!/usr/bin/env python3
"""
Athena — Intelligence Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Athena. I am the Intelligence Director. I report to Hermes. I lead 38 agents.
Areas: N/A
Skill file: skills/intelligence/athena.md
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
    """Intelligence Director: oversees research and RFCs."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    # Search knowledge base
    try:
        result = subprocess.run(["python3", str(MCP_DIR / "knowledge.py"), "list"],
                              capture_output=True, text=True, timeout=10,
                              env={**os.environ, "WEBFORGE_PROJECT": project})
        kb = json.loads(result.stdout) if result.returncode == 0 else {}
        kb_count = kb.get("data", {}).get("count", 0)
    except: kb_count = 0

    return {
        "agent": "Athena",
        "action": "research",
        "knowledge_entries": kb_count,
        "message": f"I am Athena (Intelligence Director). I oversee research and RFCs. Knowledge base has {kb_count} entries. I report to Hermes.",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "status"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
