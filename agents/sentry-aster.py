#!/usr/bin/env python3
"""
SentryAster — Quality Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Sentry-Aster. I am a I review test scripts written by Pixel agents agent. I report to Sentry-Core.
Areas: 81-82
Skill file: skills/quality/sentry-aster.md
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
    """Test agent: writes and runs test review for areas 81-82."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    # Run tests
    try:
        result = subprocess.run(["python3", str(MCP_DIR / "quality.py"), "check"],
                              capture_output=True, text=True, timeout=60,
                              env={**os.environ, "WEBFORGE_PROJECT": project})
        check_data = json.loads(result.stdout) if result.returncode == 0 else {}
    except: check_data = {}

    return {
        "agent": "SentryAster",
        "action": "test",
        "test_type": "test review",
        "areas": "81-82",
        "message": f"I am SentryAster. I write and run test review for areas 81-82. I report to my team lead.",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "test"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
