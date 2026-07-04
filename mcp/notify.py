#!/usr/bin/env python3
"""
Notify MCP — the phone system (solves the 3 breakdowns)

THE PROBLEM (from the developer):
  1. Hermes writes a task for Athena → Athena doesn't know
  2. Athena assigns to Senior → Senior doesn't know
  3. Junior finishes → nobody upstream gets pinged

Nobody gets a notification at any step. The board changes but
nobody's phone rings.

THE SOLUTION:
  Every task event (create, assign, move, done, block) sends a
  notification to the relevant agent's inbox. The next time that
  agent is @mentioned or /resume is called, they see their
  unread notifications.

  Additionally, /standup shows unread notifications so the developer
  knows what needs attention.

Notification events:
  - TASK_CREATED    → notify the department director
  - TASK_ASSIGNED   → notify the assigned agent
  - TASK_DONE       → notify the reporter (who created it)
  - TASK_BLOCKED    → notify Hermes (COO) + developer
  - ESCALATION      → notify developer (CEO)
  - REVIEW_NEEDED   → notify Minos (Quality)

Notifications are:
  - Written to .webforge/notifications/<agent-name>.json
  - Shown in /standup
  - Shown when agent is @mentioned
  - Marked read when acknowledged
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root
from memory import session_append


def info() -> dict:
    return {
        "id": "m-notify",
        "name": "Notify MCP",
        "tier": 1,
        "owner": "Hermes",
        "job": "The phone system. Sends notifications when tasks are created, assigned, done, or blocked. Nobody is left in the dark.",
    }


# ── Paths ──
def notifications_dir() -> Path:
    d = get_project_root() / ".webforge" / "notifications"
    d.mkdir(parents=True, exist_ok=True)
    return d

def agent_inbox(agent_name: str) -> Path:
    """Each agent has their own inbox file."""
    safe_name = agent_name.lower().replace(" ", "-").replace("@", "")
    return notifications_dir() / f"{safe_name}.json"


# ── Department routing (who gets notified for what) ──
DEPARTMENT_DIRECTORS = {
    "build": "Hephaestus",
    "frontend": "Aurora",
    "backend": "Titan",
    "database": "Zephyr",
    "intelligence": "Athena",
    "quality": "Minos",
    "documentation": "Thoth",
    "meta": "Daedalus",
    "hr": "Voss",
    "executive": "Hermes",
}

# Task type → department → director
TASK_TYPE_TO_DEPT = {
    "feature": "build",
    "bugfix": "build",
    "refactor": "build",
    "test": "quality",
    "docs": "documentation",
    "architecture": "intelligence",
}


# ── Send a notification ──
def notify(agent_name: str, event: str, message: str, task_id: str = "",
           from_agent: str = "System") -> McpResult:
    """
    Send a notification to an agent's inbox.

    Args:
        agent_name: Who to notify (e.g. "Hephaestus", "Developer")
        event: Type of event (TASK_CREATED, TASK_ASSIGNED, TASK_DONE, TASK_BLOCKED, ESCALATION)
        message: The notification message
        task_id: Related task (if any)
        from_agent: Who sent the notification
    """
    inbox = agent_inbox(agent_name)

    # Load existing inbox
    if inbox.exists():
        data = json.loads(inbox.read_text())
    else:
        data = {"notifications": [], "next_id": 1}

    # Add notification
    notif_id = f"n-{data['next_id']:03d}"
    data["next_id"] += 1

    notification = {
        "id": notif_id,
        "event": event,
        "message": message,
        "task_id": task_id,
        "from": from_agent,
        "to": agent_name,
        "timestamp": utc_now(),
        "read": False,
    }
    data["notifications"].append(notification)

    # Save inbox
    inbox.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    # Also log to session
    event_emoji = {
        "TASK_CREATED": "📝",
        "TASK_ASSIGNED": "📤",
        "TASK_DONE": "✅",
        "TASK_BLOCKED": "🚫",
        "ESCALATION": "📤",
        "REVIEW_NEEDED": "🔍",
        "RFC_GENERATED": "📋",
        "RFC_APPROVED": "✅",
        "QUALITY_CHECK": "🔍",
    }.get(event, "🔔")

    session_append(
        f"NOTIFY {event_emoji} → @{agent_name}: {message}",
        agent=from_agent, kind="note"
    )

    write_log("Notify", from_agent, "notify",
              {"to": agent_name, "event": event, "task_id": task_id})

    return success({
        "notification_id": notif_id,
        "to": agent_name,
        "event": event,
        "message": f"🔔 Notification sent to @{agent_name}: {message}",
    })


# ── Notify on task created ──
def notify_task_created(task_id: str, title: str, task_type: str,
                        from_agent: str = "Hermes") -> McpResult:
    """When a task is created, notify Hermes (COO) — he coordinates routing."""
    dept = TASK_TYPE_TO_DEPT.get(task_type, "build")
    director = DEPARTMENT_DIRECTORS.get(dept, "Hephaestus")

    return notify(
        agent_name="Hermes",
        event="TASK_CREATED",
        message=f"New task {task_id}: {title} (type: {task_type}). Suggested route: @{director} ({dept}). Route with: /dispatch-route {task_id}",
        task_id=task_id,
        from_agent=from_agent,
    )


# ── Notify on task assigned ──
def notify_task_assigned(task_id: str, title: str, assigned_to: str,
                         from_agent: str = "Hermes") -> McpResult:
    """When a task is assigned to an agent, notify that agent."""
    return notify(
        agent_name=assigned_to,
        event="TASK_ASSIGNED",
        message=f"Task {task_id} assigned to you: {title}. Start working on it.",
        task_id=task_id,
        from_agent=from_agent,
    )


# ── Notify on task done ──
def notify_task_done(task_id: str, title: str, done_by: str,
                     from_agent: str = "Hephaestus") -> McpResult:
    """When a task is done, notify the reporter (who created it)."""
    # Notify the developer (CEO)
    notify(
        agent_name="Developer",
        event="TASK_DONE",
        message=f"Task {task_id} completed by @{done_by}: {title}. Quality checks may be needed: /check {task_id}",
        task_id=task_id,
        from_agent=from_agent,
    )

    # Also notify Minos (Quality) that a review is needed
    notify(
        agent_name="Minos",
        event="REVIEW_NEEDED",
        message=f"Task {task_id} marked done by @{done_by}: {title}. Run quality check: /check {task_id}",
        task_id=task_id,
        from_agent=from_agent,
    )

    return success({"message": f"Notifications sent: Developer + @Minos for task {task_id}"})


# ── Notify on task blocked ──
def notify_task_blocked(task_id: str, title: str, reason: str,
                        from_agent: str = "Hephaestus") -> McpResult:
    """When a task is blocked, notify Hermes and the developer."""
    notify(
        agent_name="Hermes",
        event="TASK_BLOCKED",
        message=f"Task {task_id} BLOCKED: {title}. Reason: {reason}. Needs attention.",
        task_id=task_id,
        from_agent=from_agent,
    )
    notify(
        agent_name="Developer",
        event="TASK_BLOCKED",
        message=f"🚫 Task {task_id} blocked: {reason}. See /standup for details.",
        task_id=task_id,
        from_agent=from_agent,
    )
    return success({"message": f"Block notifications sent: @Hermes + Developer"})


# ── Read an agent's inbox ──
def read_inbox(agent_name: str, unread_only: bool = True) -> McpResult:
    """Read an agent's notification inbox."""
    inbox = agent_inbox(agent_name)
    if not inbox.exists():
        return success({"notifications": [], "count": 0, "unread": 0})

    data = json.loads(inbox.read_text())
    notifications = data.get("notifications", [])

    if unread_only:
        notifications = [n for n in notifications if not n["read"]]

    unread_count = sum(1 for n in data.get("notifications", []) if not n["read"])

    return success({
        "agent": agent_name,
        "notifications": notifications,
        "count": len(notifications),
        "unread": unread_count,
    })


# ── Mark notifications as read ──
def mark_read(agent_name: str, notification_id: str = None) -> McpResult:
    """Mark notifications as read (all or specific one)."""
    inbox = agent_inbox(agent_name)
    if not inbox.exists():
        return success({"message": "No inbox found"})

    data = json.loads(inbox.read_text())
    marked = 0

    for n in data["notifications"]:
        if notification_id is None or n["id"] == notification_id:
            if not n["read"]:
                n["read"] = True
                marked += 1

    inbox.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return success({"marked_read": marked, "message": f"Marked {marked} notification(s) as read"})


# ── Get all unread notifications (for /standup) ──
def get_all_unread() -> list:
    """Get all unread notifications across all agents (for standup)."""
    all_unread = []
    if not notifications_dir().exists():
        return all_unread

    for inbox_file in notifications_dir().glob("*.json"):
        agent_name = inbox_file.stem
        data = json.loads(inbox_file.read_text())
        for n in data.get("notifications", []):
            if not n["read"]:
                n["agent"] = agent_name
                all_unread.append(n)

    # Sort by timestamp (newest last)
    all_unread.sort(key=lambda n: n["timestamp"])
    return all_unread


# ── CLI ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Notify MCP — the phone system")
        print("Usage: python notify.py <command> [args]")
        print()
        print("Commands:")
        print("  send <agent> <event> <message> [task_id]  Send a notification")
        print("  inbox <agent> [unread]                     Read an agent's inbox")
        print("  read <agent> [notif_id]                    Mark notifications as read")
        print("  all-unread                                  Show all unread (for standup)")
        print("  task-created <id> <title> <type>           Notify on task created")
        print("  task-assigned <id> <title> <agent>         Notify on task assigned")
        print("  task-done <id> <title> <done_by>           Notify on task done")
        print("  task-blocked <id> <title> <reason>         Notify on task blocked")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "send":
        agent = sys.argv[2]
        event = sys.argv[3]
        message = sys.argv[4]
        task_id = sys.argv[5] if len(sys.argv) > 5 else ""
        result = notify(agent, event, message, task_id)
        print(result.data.get("message", result.to_dict()))
    elif cmd == "inbox":
        agent = sys.argv[2]
        unread = sys.argv[3] != "all" if len(sys.argv) > 3 else True
        result = read_inbox(agent, unread_only=unread)
        if result.ok:
            data = result.data
            print(f"\n📬 INBOX — @{agent} ({data['unread']} unread)\n")
            for n in data["notifications"]:
                emoji = {"TASK_CREATED": "📝", "TASK_ASSIGNED": "📤", "TASK_DONE": "✅",
                         "TASK_BLOCKED": "🚫", "ESCALATION": "📤", "REVIEW_NEEDED": "🔍"}.get(n["event"], "🔔")
                print(f"  {emoji} [{n['id']}] {n['event']}: {n['message']}")
                print(f"     From: @{n['from']} | {n['timestamp'][:19]}")
                print()
            if not data["notifications"]:
                print("  (no unread notifications)")
        else:
            print(result.error)
    elif cmd == "read":
        agent = sys.argv[2]
        notif_id = sys.argv[3] if len(sys.argv) > 3 else None
        result = mark_read(agent, notif_id)
        print(result.data.get("message", result.to_dict()))
    elif cmd == "all-unread":
        unread = get_all_unread()
        if not unread:
            print("✅ No unread notifications. Everyone is caught up.")
        else:
            print(f"📬 UNREAD NOTIFICATIONS ({len(unread)})\n")
            for n in unread:
                emoji = {"TASK_CREATED": "📝", "TASK_ASSIGNED": "📤", "TASK_DONE": "✅",
                         "TASK_BLOCKED": "🚫", "ESCALATION": "📤", "REVIEW_NEEDED": "🔍"}.get(n["event"], "🔔")
                print(f"  {emoji} → @{n['agent']}: {n['message']}")
                print(f"     From: @{n['from']} | {n['timestamp'][:19]}")
                print()
    elif cmd == "task-created":
        result = notify_task_created(sys.argv[2], sys.argv[3], sys.argv[4])
        print(result.data.get("message", result.to_dict()))
    elif cmd == "task-assigned":
        result = notify_task_assigned(sys.argv[2], sys.argv[3], sys.argv[4])
        print(result.data.get("message", result.to_dict()))
    elif cmd == "task-done":
        result = notify_task_done(sys.argv[2], sys.argv[3], sys.argv[4])
        print(result.data.get("message", result.to_dict()))
    elif cmd == "task-blocked":
        result = notify_task_blocked(sys.argv[2], sys.argv[3], sys.argv[4])
        print(result.data.get("message", result.to_dict()))
    else:
        print(f"Unknown command: {cmd}")
