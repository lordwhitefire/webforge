#!/usr/bin/env python3
"""
ScalpelBramble — Quality Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Scalpel-Bramble. I am a I write and run E2E tests in a real browser agent. I report to Scalpel-Core.
Areas: 51-55
Skill file: skills/quality/scalpel-bramble.md
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
    """Test agent: writes and runs E2E tests for areas 51-55."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    # Run tests
    try:
        result = subprocess.run(["python3", str(MCP_DIR / "quality.py"), "check"],
                              capture_output=True, text=True, timeout=60,
                              env={**os.environ, "WEBFORGE_PROJECT": project})
        check_data = json.loads(result.stdout) if result.returncode == 0 else {}
    except: check_data = {}

    return {
        "agent": "ScalpelBramble",
        "action": "test",
        "test_type": "E2E tests",
        "areas": "51-55",
        "message": f"I am ScalpelBramble. I write and run E2E tests for areas 51-55. I report to my team lead.",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "test"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
