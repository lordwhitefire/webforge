#!/usr/bin/env python3
"""
Bug MCP — bug tracking (replaces 18-agent Pulse team)

Industry pattern: Bugs are tracked issues (Jira, Linear, GitHub Issues).
In WebForge, bugs are just tasks with type='bugfix' in the Kanban board.

When a bug is found:
  1. /bug "description" → creates a bugfix task in backlog
  2. /build → proposes the bug (two-way door, no RFC needed)
  3. /task-approve → agent fixes it
  4. /task-done → quality check runs (regression test should be added)

Regression testing: when a bug is fixed, a test should be written
to ensure it never comes back.
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult
from memory import session_append
from task import task_create, task_list, load_board


def info() -> dict:
    return {
        "id": "m-bug",
        "name": "Bug MCP",
        "tier": 4,
        "owner": "Minos",
        "job": "Track bugs as tasks. Replaces 18-agent Pulse team with simple bug → task → fix → test flow.",
    }


def bug_create(description: str, severity: str = "medium") -> McpResult:
    """
    Create a bug as a bugfix task in the Kanban board.
    Bugs are two-way doors — no RFC needed, fast fix.

    severity: low, medium, high, critical
    """
    # Severity maps to effort
    effort_map = {"low": "S", "medium": "S", "high": "M", "critical": "M"}
    effort = effort_map.get(severity.lower(), "S")

    # Create the task
    result = task_create(
        title=f"[BUG:{severity.upper()}] {description}",
        task_type="bugfix",
        effort=effort,
    )

    if not result.ok:
        return result

    task = result.data["task"]
    task_id = result.data["id"]

    # Log specifically as a bug
    session_append(
        f"BUG REPORTED — {task_id}: {description} (severity: {severity})",
        agent="Developer", kind="note"
    )
    write_log("Bug", "Minos", "bug_create",
              {"task_id": task_id, "description": description, "severity": severity})

    return success({
        "task_id": task_id,
        "description": description,
        "severity": severity,
        "message": (
            f"🐛 BUG CREATED — {task_id}\n"
            f"  Description: {description}\n"
            f"  Severity: {severity}\n"
            f"  Type: bugfix (two-way door — no RFC needed)\n\n"
            f"  To fix: /build → /task-approve {task_id}\n"
            f"  When done, write a regression test to prevent recurrence."
        ),
    })


def bug_list() -> McpResult:
    """List all open bugs (bugfix tasks not done)."""
    board = load_board()
    bugs = [t for t in board["tasks"] if t["type"] == "bugfix" and t["status"] != "done"]

    if not bugs:
        return success({"bugs": [], "count": 0, "message": "No open bugs. 🎉"})

    lines = []
    lines.append("=" * 60)
    lines.append(f"OPEN BUGS ({len(bugs)})")
    lines.append("=" * 60)
    lines.append("")

    for b in bugs:
        # Extract severity from title
        severity = "unknown"
        if "[BUG:" in b["title"]:
            severity = b["title"].split("[BUG:")[1].split("]")[0].lower()

        severity_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(severity, "⚪")

        # Clean title
        clean_title = b["title"]
        if "] " in clean_title:
            clean_title = clean_title.split("] ", 1)[1]

        lines.append(f"  {severity_emoji} {b['id']}: {clean_title}")
        lines.append(f"     Status: {b['status']} | Severity: {severity} | Owner: {b.get('owner', 'unassigned')}")
        lines.append("")

    lines.append("=" * 60)
    lines.append(f"Total open bugs: {len(bugs)}")
    lines.append("=" * 60)

    return success({"bugs": bugs, "count": len(bugs), "output": "\n".join(lines)})


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Bug MCP — bug tracking")
        print("Usage: python bug.py <command> [args]")
        print()
        print("Commands:")
        print("  create <description> [severity]  Report a bug (creates bugfix task)")
        print("  list                             List all open bugs")
        print()
        print("Severity: low, medium, high, critical")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "create":
        description = sys.argv[2] if len(sys.argv) > 2 else ""
        severity = sys.argv[3] if len(sys.argv) > 3 else "medium"
        if description:
            result = bug_create(description, severity)
            print(result.data.get("message", result.to_dict()))
        else:
            print("Usage: create <description> [severity]")
    elif cmd == "list":
        result = bug_list()
        print(result.data.get("output", result.to_dict()))
    else:
        print(f"Unknown command: {cmd}")
