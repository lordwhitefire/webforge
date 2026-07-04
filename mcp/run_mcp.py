#!/usr/bin/env python3
"""
WebForge MCP Runner
Single entry point to call any MCP from the command line.

Usage:
    python run_mcp.py <mcp_name> <command> [args...]

Examples:
    python run_mcp.py pipeline status
    python run_mcp.py memory status
    python run_mcp.py skill_loader get Probe-Orion
    python run_mcp.py hr execute Voss
"""

import sys
import os
import importlib.util
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log

MCP_DIR = Path(__file__).parent


def list_mcps():
    """List all available MCPs."""
    mcps = []
    for f in sorted(MCP_DIR.glob("*.py")):
        if f.name in ["__init__.py", "common.py", "run_mcp.py"]:
            continue
        # Try to import and get info
        try:
            spec = importlib.util.spec_from_file_location(f.stem, f)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "info"):
                # Some MCPs have info() function
                try:
                    info = mod.info()
                    mcps.append({
                        "file": f.name,
                        "name": info.get("name", f.stem),
                        "tier": info.get("tier", "?"),
                        "owner": info.get("owner", "?"),
                    })
                    continue
                except Exception as _e:
                    write_log("RunMCP", "Runner", "get MCP info", {"error": str(_e)})
            mcps.append({"file": f.name, "name": f.stem, "tier": "?", "owner": "?"})
        except Exception as e:
            mcps.append({"file": f.name, "name": f.stem, "tier": "!", "owner": f"error: {e}"})
    return mcps


def main():
    if len(sys.argv) < 2:
        print("WebForge MCP Runner")
        print("=" * 60)
        print("\nUsage: python run_mcp.py <mcp_name> <command> [args...]\n")
        print("Available MCPs:")
        mcps = list_mcps()
        for m in mcps:
            print(f"  {m['file']:30s}  T{m['tier']}  owner: {m['owner']}")
        print(f"\nTotal: {len(mcps)} MCPs")
        sys.exit(0)

    mcp_name = sys.argv[1].replace(".py", "")
    mcp_file = MCP_DIR / f"{mcp_name}.py"

    if not mcp_file.exists():
        print(f"Error: MCP '{mcp_name}' not found at {mcp_file}")
        print("\nAvailable MCPs:")
        for m in list_mcps():
            print(f"  {m['file']}")
        sys.exit(1)

    # Import and run
    spec = importlib.util.spec_from_file_location(mcp_name, mcp_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Pass remaining args to the MCP
    sys.argv = [mcp_file.name] + sys.argv[2:]

    # The MCP's __main__ block will run
    # We need to exec the file's main block
    code = mcp_file.read_text()
    # Find the if __name__ == "__main__" block and run it
    if 'if __name__' in code:
        exec(compile(code, str(mcp_file), "exec"), mod.__dict__)
    else:
        print(f"MCP {mcp_name} has no main block.")


if __name__ == "__main__":
    main()
