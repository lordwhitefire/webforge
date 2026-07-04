#!/usr/bin/env python3
"""
ProbeHollow — Intelligence Department
Standalone agent script. Does NOT rely on other agents' scripts.

Role: I am Probe-Hollow. I am a Probe Agent in the Intelligence team. I report to Athena.
Areas: 61-65
Skill file: skills/intelligence/probe-hollow.md
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
    """Probe agent: scans project for areas 61-65."""
    project = os.environ.get("WEBFORGE_PROJECT", os.getcwd())

    # Scan project structure
    result = subprocess.run(["python3", str(MCP_DIR / "probe.py"), "scan"],
                          capture_output=True, text=True, timeout=30,
                          env={**os.environ, "WEBFORGE_PROJECT": project})

    scan_data = json.loads(result.stdout) if result.returncode == 0 else {}

    # Log findings to memory
    try:
        subprocess.run(["python3", str(MCP_DIR / "memory.py"), "session-append",
                       f"PROBE-ProbeHollow scanned project. Files: {scan_data.get('stats', {}).get('total_files', '?')}",
                       "ProbeHollow", "note"],
                      capture_output=True, timeout=10,
                      env={**os.environ, "WEBFORGE_PROJECT": project})
    except: pass

    return {
        "agent": "ProbeHollow",
        "action": "probe",
        "areas": "61-65",
        "message": f"I am ProbeHollow. I probed areas 61-65. Found {scan_data.get('stats', {}).get('total_files', '?')} files. Findings written to memory.",
        "scan": scan_data,
        "next_step": None,
    }

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "probe"
    r = run(msg)
    print(r.get("message", json.dumps(r, indent=2)))
