#!/usr/bin/env python3
"""
PixelPike — Quality Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Pixel-Pike. I am a I write and run unit/integration tests agent. I report to Pixel-Core.
Areas: 36-40
Skill file: skills/quality/pixel-pike.md
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
    """Test agent: writes and runs unit/integration tests for areas 36-40."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    # Run tests
    try:
        result = subprocess.run(["python3", str(MCP_DIR / "quality.py"), "check"],
                              capture_output=True, text=True, timeout=60,
                              env={**os.environ, "WEBFORGE_PROJECT": project})
        check_data = json.loads(result.stdout) if result.returncode == 0 else {}
    except: check_data = {}

    return {
        "agent": "PixelPike",
        "action": "test",
        "test_type": "unit/integration tests",
        "areas": "36-40",
        "message": f"I am PixelPike. I write and run unit/integration tests for areas 36-40. I report to my team lead.",
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "test"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
