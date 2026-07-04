#!/usr/bin/env python3
"""
OdinWisp — Intelligence Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Odin-Wisp. I am an Odin Agent in the Intelligence team. I report to Athena.
Areas: 41-45
Skill file: skills/intelligence/odin-wisp.md
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
    """Odin agent: researches standards for areas 41-45."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    # Search knowledge base for existing research
    try:
        result = subprocess.run(["python3", str(MCP_DIR / "knowledge.py"), "search", message or "standards"],
                              capture_output=True, text=True, timeout=10,
                              env={**os.environ, "WEBFORGE_PROJECT": project})
        kb = json.loads(result.stdout) if result.returncode == 0 else {}
    except: kb = {}

    findings = kb.get("data", {}).get("results", [])

    # Log research to memory
    try:
        subprocess.run(["python3", str(MCP_DIR / "memory.py"), "session-append",
                       f"ODIN-OdinWisp researched: {message[:80]}",
                       "OdinWisp", "note"],
                      capture_output=True, timeout=10,
                      env={**os.environ, "WEBFORGE_PROJECT": project})
    except: pass

    return {
        "agent": "OdinWisp",
        "action": "research",
        "areas": "41-45",
        "message": f"I am OdinWisp. I researched standards for areas 41-45. Topic: {message}. Found {len(findings)} existing knowledge entries.",
        "knowledge_results": findings,
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "research standards"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
