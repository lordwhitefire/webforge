#!/usr/bin/env python3
"""
Standup MCP — the daily sync (Hermes's new job)

Industry pattern: Daily standup (Atlassian, Agile). Three questions:
  1. What did we do last session? (from session log)
  2. What are we doing now? (from Kanban board — DOING column)
  3. What's blocking us? (from blocked tasks + open bugs)

Also shows:
  - Board summary (backlog/todo/doing/done counts)
  - Open bugs with severity
  - Suggested next action (/build or /unblock)

When /resume is called, it reads memory THEN calls standup at the end.
One command to start every session.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root
from memory import session_read, read_rules, list_adrs, session_append


def info() -> dict:
    return {
        "id": "m-standup",
        "name": "Standup MCP",
        "tier": 2,
        "owner": "Hermes",
        "job": "Daily sync: what we did, what we're doing, what's blocked. Hermes's new role as COO.",
    }


def standup_run() -> McpResult:
    """
    Run the standup. Shows:
      1. Last session activity (what we did)
      2. In progress (what we're doing)
      3. Blocked (what's stopping us)
      4. Board summary
      5. Open bugs
      6. Suggested next action
    """
    lines = []
    lines.append("=" * 60)
    lines.append("🏃 WEBFORGE STANDUP")
    lines.append(f"   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("=" * 60)

    # ── 1. LAST SESSION (what we did) ──
    lines.append("")
    lines.append("📋 LAST SESSION (recent activity)")
    lines.append("─" * 40)

    result = session_read(days=7)
    entries = result.data.get("entries", [])

    if entries:
        # Show last 10 entries
        for entry in entries[-10:]:
            # Truncate long entries
            if len(entry) > 120:
                entry = entry[:117] + "..."
            lines.append(f"  {entry}")
    else:
        lines.append("  (no session history yet — this is a new project)")

    # ── 2. IN PROGRESS (what we're doing) ──
    lines.append("")
    lines.append("🔄 IN PROGRESS")
    lines.append("─" * 40)

    try:
        from task import load_board
        board = load_board()
        tasks = board.get("tasks", [])

        doing = [t for t in tasks if t["status"] == "doing"]
        todo = [t for t in tasks if t["status"] == "todo"]
        backlog = [t for t in tasks if t["status"] == "backlog"]
        done = [t for t in tasks if t["status"] == "done"]
        blocked = [t for t in tasks if t["status"] == "blocked"]

        if doing:
            for t in doing:
                owner = t.get("owner", "unassigned")
                effort_badge = {"S": "🟢", "M": "🟡", "L": "🔴"}.get(t.get("effort", ""), "⚪")
                lines.append(f"  {effort_badge} {t['id']}: {t['title']} [{owner}]")
        else:
            lines.append("  (nothing in progress — run /build to start a task)")
    except:
        doing = []
        todo = []
        backlog = []
        done = []
        blocked = []
        lines.append("  (task board not available)")

    # ── 3. BLOCKED (what's stopping us) ──
    lines.append("")
    lines.append("🚫 BLOCKED")
    lines.append("─" * 40)

    has_blockers = False

    # Blocked tasks
    try:
        if blocked:
            has_blockers = True
            for t in blocked:
                reason = t.get("block_reason", "(no reason given)")
                lines.append(f"  ⛔ {t['id']}: {t['title']}")
                lines.append(f"     Reason: {reason}")
                lines.append(f"     → Fix the issue, then: /task-move {t['id']} todo")
    except:
        pass

    # Open bugs (high severity = blockers)
    try:
        from bug import bug_list
        bug_result = bug_list()
        bugs = bug_result.data.get("bugs", [])
        high_bugs = [b for b in bugs if "HIGH" in b.get("title", "").upper() or "CRITICAL" in b.get("title", "").upper()]
        if high_bugs:
            has_blockers = True
            lines.append("")
            for b in high_bugs:
                clean_title = b["title"].split("] ", 1)[-1] if "] " in b["title"] else b["title"]
                lines.append(f"  🐛 {b['id']}: {clean_title}")
                lines.append(f"     → Fix: /build → /task-approve {b['id']}")
    except:
        pass

    if not has_blockers:
        lines.append("  ✅ No blockers — full speed ahead!")

    # ── 4. BOARD SUMMARY ──
    lines.append("")
    lines.append("📊 BOARD SUMMARY")
    lines.append("─" * 40)

    try:
        lines.append(f"  Backlog: {len(backlog)} | TODO: {len(todo)} | DOING: {len(doing)} | Done: {len(done)} | Blocked: {len(blocked)}")

        # Open bugs count
        try:
            from bug import bug_list
            bug_result = bug_list()
            bugs = bug_result.data.get("bugs", [])
            if bugs:
                lines.append(f"  Open bugs: {len(bugs)}")
        except:
            pass
    except:
        pass

    # ── 5. RULES REMINDER ──
    lines.append("")
    lines.append("📏 ACTIVE RULES")
    lines.append("─" * 40)

    rules_text = read_rules()
    if rules_text and rules_text != "(no rules set)":
        # Show just the rule lines (not headers)
        for line in rules_text.split("\n"):
            if line.strip().startswith("-"):
                lines.append(f"  {line.strip()}")
    else:
        lines.append("  (no rules set — use /correct when AI does something wrong)")

    # ── 6. NOTIFICATIONS (the phone system) ──
    lines.append("")
    lines.append("📬 NOTIFICATIONS")
    lines.append("─" * 40)

    try:
        from notify import get_all_unread
        unread = get_all_unread()
        if unread:
            for n in unread:
                emoji = {"TASK_CREATED": "📝", "TASK_ASSIGNED": "📤", "TASK_DONE": "✅",
                         "TASK_BLOCKED": "🚫", "ESCALATION": "📤", "REVIEW_NEEDED": "🔍"}.get(n["event"], "🔔")
                lines.append(f"  {emoji} → @{n['agent']}: {n['message'][:80]}")
        else:
            lines.append("  ✅ No unread notifications. Everyone is caught up.")
    except:
        lines.append("  (notification system not available)")

    # ── 7. SUGGESTED NEXT ACTION ──
    lines.append("")
    lines.append("💡 SUGGESTED NEXT ACTION")
    lines.append("─" * 40)

    try:
        if blocked:
            lines.append(f"  → Unblock a task: /unblock {blocked[0]['id']}")
        elif doing and len(doing) >= 2:
            lines.append(f"  → Finish in-progress work: /task-done {doing[0]['id']}")
        elif doing:
            lines.append(f"  → Continue: {doing[0]['id']} — {doing[0]['title']}")
            lines.append(f"    Or start next: /build")
        elif todo or backlog:
            lines.append("  → Start next task: /build")
        else:
            lines.append("  → Create a task: /task \"description\" feature area effort")
            lines.append("    Then: /build")
    except:
        lines.append("  → /build to see next task")

    lines.append("")
    lines.append("=" * 60)
    lines.append("STANDUP COMPLETE — you're caught up.")
    lines.append("=" * 60)

    # Log
    session_append("STANDUP RUN", agent="Hermes", kind="note")
    write_log("Standup", "Hermes", "standup_run", {})

    return success({"output": "\n".join(lines)})
