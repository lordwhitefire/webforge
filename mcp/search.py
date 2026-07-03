#!/usr/bin/env python3
"""
MCP 5 — Search MCP
Tier 1 — Foundation

Search codebase using ripgrep (rg) or Python's re as fallback.
"""

import sys
import json
import subprocess
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, McpResult


def info() -> dict:
    return {
        "id": "m05",
        "name": "Search MCP",
        "tier": 1,
        "owner": "Everyone",
        "job": "Search codebase (grep, glob, find). Every agent uses this.",
    }


def search(pattern: str, root: str = ".", file_glob: str = "*") -> McpResult:
    """Search for a pattern in files under root."""
    p = Path(root).expanduser()
    if not p.exists():
        return fail(f"Root not found: {root}")

    matches = []
    # Try ripgrep first
    try:
        cmd = ["rg", "--no-heading", "-n", "--type", "ts",
               pattern, str(p)]
        if file_glob != "*":
            cmd = ["rg", "--no-heading", "-n", "-g", file_glob,
                   pattern, str(p)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n")[:50]:
                if ":" in line:
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        matches.append({"file": parts[0], "line": int(parts[1]),
                                        "text": parts[2][:200]})
        write_log("Search", "Unknown", "search",
                  {"pattern": pattern, "matches": len(matches), "tool": "ripgrep"})
        return success({"pattern": pattern, "matches": matches, "count": len(matches)})
    except FileNotFoundError:
        # Fallback to Python regex
        pass
    except subprocess.TimeoutExpired:
        return fail("Search timed out")

    # Python fallback
    try:
        regex = re.compile(pattern, re.IGNORECASE)
        for f in p.rglob(file_glob):
            if not f.is_file():
                continue
            if ".git" in f.parts or "node_modules" in f.parts:
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(content.split("\n"), 1):
                    if regex.search(line):
                        matches.append({"file": str(f), "line": i, "text": line.strip()[:200]})
                        if len(matches) >= 50:
                            break
                if len(matches) >= 50:
                    break
            except:
                continue
        write_log("Search", "Unknown", "search",
                  {"pattern": pattern, "matches": len(matches), "tool": "python"})
        return success({"pattern": pattern, "matches": matches, "count": len(matches)})
    except Exception as e:
        return fail(f"Search error: {e}")


def find_files(pattern: str, root: str = ".") -> McpResult:
    """Find files matching a glob pattern."""
    p = Path(root).expanduser()
    matches = []
    for f in p.rglob(pattern):
        if ".git" in f.parts or "node_modules" in f.parts:
            continue
        matches.append(str(f))
    write_log("Search", "Unknown", "find_files",
              {"pattern": pattern, "matches": len(matches)})
    return success({"pattern": pattern, "files": matches[:100], "count": len(matches)})


def run(action: str = "default", **kwargs) -> McpResult:
    if action == "info":
        return success(info())
    elif action == "search":
        return search(kwargs.get("pattern", ""), kwargs.get("root", "."),
                      kwargs.get("file_glob", "*"))
    elif action == "find":
        return find_files(kwargs.get("pattern", "*"), kwargs.get("root", "."))
    else:
        return fail(f"Unknown action: {action}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Search MCP")
        print("Usage: python search.py <command> [args]")
        print("Commands: info, search <pattern> [root] [file_glob], find <pattern> [root]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "search":
        pattern = sys.argv[2]
        root = sys.argv[3] if len(sys.argv) > 3 else "."
        file_glob = sys.argv[4] if len(sys.argv) > 4 else "*"
        r = search(pattern, root, file_glob)
        print(r.to_dict())
    elif cmd == "find":
        r = find_files(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ".")
        print(r.to_dict())
    else:
        print(f"Unknown command: {cmd}")
