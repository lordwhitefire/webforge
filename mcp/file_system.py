#!/usr/bin/env python3
"""
MCP 4 — File System MCP
Tier 1 — Foundation

Read/write/delete/list files. Used by every agent.
"""

import sys
import json
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult


def info() -> dict:
    return {
        "id": "m04",
        "name": "File System MCP",
        "tier": 1,
        "owner": "Everyone",
        "job": "Read/write/delete files. Foundation for all agents.",
    }


def read(path: str) -> McpResult:
    """Read a file's contents."""
    p = Path(path).expanduser()
    if not p.exists():
        return fail(f"File not found: {path}")
    if not p.is_file():
        return fail(f"Not a file: {path}")
    try:
        content = p.read_text(encoding="utf-8")
        write_log("FileSystem", "Unknown", "read", {"path": path, "chars": len(content)})
        return success({"path": str(p), "content": content, "chars": len(content)})
    except Exception as e:
        return fail(f"Read error: {e}")


def write(path: str, content: str, agent: str = "Unknown") -> McpResult:
    """Write content to a file. Creates parent dirs."""
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.write_text(content, encoding="utf-8")
        write_log("FileSystem", agent, "write",
                  {"path": str(p), "chars": len(content), "lines": content.count("\n") + 1})
        return success({"path": str(p), "bytes": len(content), "lines": content.count("\n") + 1})
    except Exception as e:
        return fail(f"Write error: {e}")


def append(path: str, content: str, agent: str = "Unknown") -> McpResult:
    """Append content to a file."""
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(p, "a", encoding="utf-8") as f:
            f.write(content)
        write_log("FileSystem", agent, "append", {"path": str(p), "chars": len(content)})
        return success({"path": str(p), "appended": len(content)})
    except Exception as e:
        return fail(f"Append error: {e}")


def list_dir(path: str) -> McpResult:
    """List files and folders in a directory."""
    p = Path(path).expanduser()
    if not p.exists():
        return fail(f"Directory not found: {path}")
    if not p.is_dir():
        return fail(f"Not a directory: {path}")
    items = []
    for item in sorted(p.iterdir()):
        items.append({
            "name": item.name,
            "type": "dir" if item.is_dir() else "file",
            "size": item.stat().st_size if item.is_file() else None,
        })
    write_log("FileSystem", "Unknown", "list_dir", {"path": str(p), "count": len(items)})
    return success({"path": str(p), "items": items, "count": len(items)})


def find(pattern: str, root: str = ".") -> McpResult:
    """Find files matching a glob pattern."""
    p = Path(root).expanduser()
    matches = list(p.glob(pattern))
    write_log("FileSystem", "Unknown", "find",
              {"pattern": pattern, "root": str(p), "matches": len(matches)})
    return success({"pattern": pattern, "matches": [str(m) for m in matches]})


def delete(path: str, agent: str = "Unknown") -> McpResult:
    """Delete a file or directory."""
    p = Path(path).expanduser()
    if not p.exists():
        return fail(f"Not found: {path}")
    try:
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        write_log("FileSystem", agent, "delete", {"path": str(p)})
        return success({"deleted": str(p)})
    except Exception as e:
        return fail(f"Delete error: {e}")


def exists(path: str) -> McpResult:
    """Check if a file or directory exists."""
    p = Path(path).expanduser()
    return success({"path": str(p), "exists": p.exists(), "is_file": p.is_file() if p.exists() else False,
                    "is_dir": p.is_dir() if p.exists() else False})


def run(action: str = "default", **kwargs) -> McpResult:
    """Main entry point."""
    if action == "info":
        return success(info())
    elif action == "read":
        return read(kwargs.get("path", ""))
    elif action == "write":
        return write(kwargs.get("path", ""), kwargs.get("content", ""),
                     kwargs.get("agent", "Unknown"))
    elif action == "append":
        return append(kwargs.get("path", ""), kwargs.get("content", ""),
                      kwargs.get("agent", "Unknown"))
    elif action == "list":
        return list_dir(kwargs.get("path", "."))
    elif action == "find":
        return find(kwargs.get("pattern", "*"), kwargs.get("root", "."))
    elif action == "delete":
        return delete(kwargs.get("path", ""), kwargs.get("agent", "Unknown"))
    elif action == "exists":
        return exists(kwargs.get("path", ""))
    else:
        return fail(f"Unknown action: {action}")


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("File System MCP")
        print("Usage: python file_system.py <command> [args]")
        print("Commands: info, read <path>, write <path> <content>, list <path>,")
        print("          find <pattern> [root], exists <path>, delete <path>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "read":
        r = read(sys.argv[2])
        if r.ok:
            print(r.data["content"])
        else:
            print(r.error)
    elif cmd == "write":
        r = write(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "",
                  sys.argv[4] if len(sys.argv) > 4 else "Unknown")
        print(r.to_dict())
    elif cmd == "list":
        r = list_dir(sys.argv[2] if len(sys.argv) > 2 else ".")
        print(r.to_dict())
    elif cmd == "find":
        r = find(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ".")
        print(r.to_dict())
    elif cmd == "exists":
        r = exists(sys.argv[2])
        print(r.to_dict())
    elif cmd == "delete":
        r = delete(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "Unknown")
        print(r.to_dict())
    else:
        print(f"Unknown command: {cmd}")
