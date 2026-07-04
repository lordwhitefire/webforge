#!/usr/bin/env python3
"""
MemoryForgotten — Documentation Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Memory-Forgotten. I am part of the Memory Team. I report to Quill.
Areas: N/A
Skill file: skills/documentation/memory_forgotten.md
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
    """Memory agent: tracks project memory and decisions."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    # Check memory status
    try:
        result = subprocess.run(["python3", str(MCP_DIR / "memory.py"), "status"],
                              capture_output=True, text=True, timeout=10,
                              env={**os.environ, "WEBFORGE_PROJECT": project})
        mem_status = json.loads(result.stdout) if result.returncode == 0 else {}
    except: mem_status = {}

    return {
        "agent": "MemoryForgotten",
        "action": "track_memory",
        "memory_status": mem_status.get("data", {}),
        "message": f"I am MemoryForgotten (Memory Team). I track project memory and follow the 300-line rule. Memory: {mem_status.get('data', {}).get('lines', '?')} lines. I report to Quill.",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "memory status"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
